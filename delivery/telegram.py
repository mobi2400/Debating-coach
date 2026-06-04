"""Telegram bot delivery.

Replaces the previous Meta WhatsApp Cloud API client. Two reasons:
- Telegram has unlimited free messages for personal bots — no
  conversation cap, no template approval, no 24-hour session window.
- `get_updates` is a pull model, so we read replies straight from
  GitHub Actions without standing up a webhook server.

Module surface mirrors the old delivery.whatsapp so every node import
keeps working without changes:
- send_message(text)
- send_digest(final_doc)
- wait_for_reply(timeout_minutes) -> str

All env reads are lazy so DEV_MODE flips take effect mid-process.
TelegramDeliveryError is raised when every send retry fails so the
scheduler workflow surfaces the failure instead of exiting silently.
"""

from __future__ import annotations

import asyncio
import os
import re
import time

try:
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:  # pragma: no cover - bootstrap envs without python-telegram-bot
    Bot = None  # type: ignore[assignment]
    TelegramError = Exception  # type: ignore[assignment]

from dotenv import load_dotenv

load_dotenv()

MAX_CHARS = 3500  # Telegram allows 4096; leave headroom for safety prefixes.
SECTION_HEADER_PATTERN = re.compile(r"^(TOPIC:.*|[A-Z][A-Z ]+)$")
SEND_RETRIES = 2
SEND_BACKOFF_SECONDS = 3
POLL_INTERVAL_SECONDS = 10
POLL_API_TIMEOUT_SECONDS = 25


class TelegramDeliveryError(RuntimeError):
    """Raised when Telegram send fails after every retry."""


def _bot_token() -> str | None:
    return os.getenv("TELEGRAM_BOT_TOKEN")


def _chat_id() -> int | None:
    raw = os.getenv("TELEGRAM_CHAT_ID")
    if not raw:
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def _dev_mode() -> bool:
    return os.getenv("DEV_MODE", "false").lower() == "true"


def _safe_console_text(text: str) -> str:
    """Windows consoles often default to cp1252 which can't render the
    pronunciation glyphs that leak in from Word Power Made Easy chunks."""
    try:
        text.encode("cp1252")
        return text
    except Exception:
        return text.encode("cp1252", errors="replace").decode("cp1252")


def _build_bot() -> "Bot | None":
    token = _bot_token()
    if Bot is None or not token:
        return None
    return Bot(token=token)


def _split_oversized_section(section: str) -> list[str]:
    parts: list[str] = []
    remaining = section.strip()
    while len(remaining) > MAX_CHARS:
        split_at = remaining.rfind("\n", 0, MAX_CHARS)
        if split_at == -1:
            split_at = MAX_CHARS
        parts.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        parts.append(remaining)
    return parts


def _extract_sections(text: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if SECTION_HEADER_PATTERN.match(line.strip()) and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [s for s in sections if s]


def _split_message(text: str) -> list[str]:
    sections = _extract_sections(text)
    if not sections:
        return _split_oversized_section(text)

    parts: list[str] = []
    current = ""
    for section in sections:
        if len(section) > MAX_CHARS:
            if current:
                parts.append(current.strip())
                current = ""
            parts.extend(_split_oversized_section(section))
            continue
        candidate = f"{current}\n\n{section}".strip() if current else section
        if len(candidate) <= MAX_CHARS:
            current = candidate
        else:
            if current:
                parts.append(current.strip())
            current = section
    if current:
        parts.append(current.strip())
    return parts


async def _send_async(bot: "Bot", chat_id: int, text: str):
    await bot.send_message(chat_id=chat_id, text=text)


def _send_single(text: str):
    bot = _build_bot()
    chat_id = _chat_id()

    if _dev_mode() or bot is None or chat_id is None:
        print(f"\n[Telegram DEV]\n{_safe_console_text(text)}\n{'=' * 40}")
        return

    last_error = ""
    for attempt in range(1, SEND_RETRIES + 2):
        try:
            asyncio.run(_send_async(bot, chat_id, text))
            print(f"[Telegram] Sent (attempt {attempt})")
            return
        except Exception as exc:
            last_error = str(exc)
            print(f"[Telegram] Send failed (attempt {attempt}): {last_error[:300]}")
            if attempt <= SEND_RETRIES:
                time.sleep(SEND_BACKOFF_SECONDS * attempt)

    raise TelegramDeliveryError(
        f"All {SEND_RETRIES + 1} Telegram send attempts failed. Last error: {last_error}"
    )


def send_message(text: str):
    if not text:
        return
    if len(text) <= MAX_CHARS:
        _send_single(text)
        return
    for part in _split_message(text):
        _send_single(part)
        time.sleep(1)


def send_digest(final_doc: str):
    send_message(final_doc)


async def _drop_pending_updates(bot: "Bot") -> int | None:
    """Return the highest update_id currently sitting in the queue so the
    poll loop only sees genuinely new messages. Returns None if the queue
    is empty."""
    updates = await bot.get_updates(limit=100, timeout=0)
    if not updates:
        return None
    return updates[-1].update_id


async def _poll_for_reply(timeout_minutes: int, chat_id: int) -> str:
    bot = _build_bot()
    if bot is None:
        return "no"

    deadline = time.time() + timeout_minutes * 60
    last_update_id = await _drop_pending_updates(bot)
    print(f"[Telegram] Waiting up to {timeout_minutes} min for a reply...")

    while time.time() < deadline:
        try:
            updates = await bot.get_updates(
                offset=(last_update_id + 1) if last_update_id is not None else None,
                timeout=POLL_API_TIMEOUT_SECONDS,
                limit=5,
            )
        except TelegramError as exc:
            print(f"[Telegram] Poll error: {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue

        for update in updates:
            last_update_id = update.update_id
            msg = getattr(update, "message", None) or getattr(update, "edited_message", None)
            if msg is None or msg.text is None:
                continue
            if msg.chat_id != chat_id:
                continue
            text = msg.text.strip()
            if not text:
                continue
            print(f"[Telegram] Received reply: {text[:80]}")
            return text

        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    print("[Telegram] Timeout — defaulting to 'no'")
    return "no"


def wait_for_reply(timeout_minutes: int = 30) -> str:
    if _dev_mode():
        try:
            return input("[Telegram DEV] Simulate reply: ").strip() or "no"
        except EOFError:
            return "no"

    chat_id = _chat_id()
    if chat_id is None or _bot_token() is None:
        return "no"

    return asyncio.run(_poll_for_reply(timeout_minutes, chat_id))
