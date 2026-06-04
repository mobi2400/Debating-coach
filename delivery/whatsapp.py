"""Meta WhatsApp Cloud API client.

Replaces the previous Twilio-based delivery. Two reasons for the switch:
- Twilio WhatsApp sandbox was downgrading our messages to SMS in
  production because the channel prefix wasn't propagating correctly.
- Meta's Cloud API has a free tier of 1000 conversations / month and
  no SMS confusion.

This module is intentionally tiny:
- `send_message(text)` — POSTs one or more text payloads to the
  Graph API, splitting on section boundaries to fit phone-friendly
  message sizes. Raises WhatsAppDeliveryError when every retry fails
  so the scheduler workflow surfaces the failure (was previously
  swallowed → silent exit 0 with nothing on your phone).
- `send_digest(final_doc)` — alias used by the daily graph.
- `wait_for_reply(timeout_minutes)` — Meta Cloud API has no polling
  endpoint. Reply detection uses a flag file written by an external
  webhook server (see docs/WHATSAPP_SETUP.md). If no webhook is
  wired, this returns "no" after timeout, so the night agent
  degrades cleanly to bedtime mode.

All env reads are lazy so DEV_MODE flips take effect mid-process.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    requests = None

from dotenv import load_dotenv

load_dotenv()

GRAPH_API_VERSION = "v19.0"
MAX_CHARS = 1500
SECTION_HEADER_PATTERN = re.compile(r"^(TOPIC:.*|[A-Z][A-Z ]+)$")
SEND_RETRIES = 2
SEND_BACKOFF_SECONDS = 3
REPLY_FLAG_FILE = Path(__file__).resolve().parents[1] / "memory" / "reply_flag.txt"


class WhatsAppDeliveryError(RuntimeError):
    """Raised when Meta Cloud API fails after every retry. The scheduler
    workflow turns this into a failed job → email notification."""


def _token() -> str | None:
    return os.getenv("WHATSAPP_TOKEN") or os.getenv("META_WHATSAPP_TOKEN")


def _phone_number_id() -> str | None:
    return os.getenv("WHATSAPP_PHONE_NUMBER_ID")


def _to_number() -> str | None:
    raw = os.getenv("YOUR_WHATSAPP_NUMBER")
    if not raw:
        return None
    # Meta wants raw country-code + number; strip + / spaces / 'whatsapp:' if present.
    cleaned = raw.strip()
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned.split(":", 1)[1]
    return cleaned.lstrip("+").replace(" ", "").replace("-", "")


def _dev_mode() -> bool:
    return os.getenv("DEV_MODE", "false").lower() == "true"


def _safe_console_text(text: str) -> str:
    try:
        text.encode("cp1252")
        return text
    except Exception:
        return text.encode("cp1252", errors="replace").decode("cp1252")


def _base_url() -> str | None:
    pid = _phone_number_id()
    if not pid:
        return None
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{pid}/messages"


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


def _post_text(url: str, headers: dict, payload: dict) -> tuple[bool, str]:
    if requests is None:
        return False, "requests library not installed"
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception as exc:
        return False, f"network: {exc}"

    if response.status_code == 200:
        return True, ""
    # Surface Meta's error body so debugging doesn't require checking the dashboard.
    return False, f"{response.status_code} {response.text[:400]}"


def _send_single(text: str):
    token = _token()
    url = _base_url()
    to = _to_number()

    if _dev_mode() or not token or not url or not to:
        print(f"\n[WhatsApp DEV]\n{_safe_console_text(text)}\n{'=' * 40}")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    last_error = ""
    for attempt in range(1, SEND_RETRIES + 2):  # initial try + retries
        ok, error = _post_text(url, headers, payload)
        if ok:
            print(f"[WhatsApp] Sent (attempt {attempt})")
            return
        last_error = error
        print(f"[WhatsApp] Send failed (attempt {attempt}): {error}")
        if attempt <= SEND_RETRIES:
            time.sleep(SEND_BACKOFF_SECONDS * attempt)

    raise WhatsAppDeliveryError(
        f"All {SEND_RETRIES + 1} send attempts failed. Last error: {last_error}"
    )


def send_message(text: str):
    if len(text) <= MAX_CHARS:
        _send_single(text)
        return
    for part in _split_message(text):
        _send_single(part)
        time.sleep(1)


def send_digest(final_doc: str):
    send_message(final_doc)


def wait_for_reply(timeout_minutes: int = 30) -> str:
    """Poll memory/reply_flag.txt — written by the optional webhook server.

    Meta Cloud API doesn't expose a 'list incoming messages' endpoint; it
    only pushes via webhook. If you wire docs/WHATSAPP_SETUP.md's webhook
    server (Render free tier), it writes the user's reply into the flag
    file and this function picks it up. With no webhook configured the
    function returns 'no' on timeout so the night agent degrades to the
    bedtime path instead of hanging.

    Set DEV_MODE=true for a stdin prompt during local tests.
    """
    if _dev_mode():
        try:
            return input("[WhatsApp DEV] Simulate reply: ").strip() or "no"
        except EOFError:
            return "no"

    deadline = time.time() + (timeout_minutes * 60)
    REPLY_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
    while time.time() < deadline:
        if REPLY_FLAG_FILE.exists():
            try:
                reply = REPLY_FLAG_FILE.read_text(encoding="utf-8").strip()
                REPLY_FLAG_FILE.unlink()
            except OSError:
                reply = ""
            if reply:
                return reply
        time.sleep(15)
    return "no"
