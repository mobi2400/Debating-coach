import os
import re
import time

from dotenv import load_dotenv

try:
    from twilio.rest import Client
    from twilio.http.http_client import TwilioHttpClient
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    Client = None
    TwilioHttpClient = None

load_dotenv()

MAX_CHARS = 1500
SECTION_HEADER_PATTERN = re.compile(r"^(TOPIC:.*|[A-Z][A-Z ]+)$")
TWILIO_TIMEOUT_SECONDS = 5
SEND_RETRY_DELAY_SECONDS = 1


def _account_sid() -> str | None:
    return os.getenv("TWILIO_ACCOUNT_SID")


def _auth_token() -> str | None:
    return os.getenv("TWILIO_AUTH_TOKEN")


def _with_whatsapp_prefix(value: str | None) -> str | None:
    """Twilio routes a message to WhatsApp only when both endpoints carry the
    'whatsapp:' channel prefix. If the env var is just '+91…' Twilio falls
    back to SMS — which is why digests were arriving as SMS. Coerce here so
    the rest of the code can pass the raw number from .env."""
    if not value:
        return value
    value = value.strip()
    if value.lower().startswith("whatsapp:"):
        return "whatsapp:" + value.split(":", 1)[1].strip()
    return f"whatsapp:{value}"


def _from_number() -> str | None:
    return _with_whatsapp_prefix(os.getenv("TWILIO_WHATSAPP_FROM"))


def _to_number() -> str | None:
    return _with_whatsapp_prefix(os.getenv("YOUR_WHATSAPP_NUMBER"))


def _dev_mode() -> bool:
    return os.getenv("DEV_MODE", "false").lower() == "true"


class WhatsAppDeliveryError(RuntimeError):
    """Raised when Twilio sends fail after every retry. Lets the scheduler
    workflow surface the failure instead of silently exiting 0 with no
    message delivered."""


def _build_client():
    sid, token = _account_sid(), _auth_token()
    if Client is None or not sid or not token:
        return None
    kwargs = {}
    if TwilioHttpClient is not None:
        kwargs["http_client"] = TwilioHttpClient(timeout=TWILIO_TIMEOUT_SECONDS)
    return Client(sid, token, **kwargs)


def _should_retry_send(exc: Exception) -> bool:
    text = str(exc).lower()
    if any(signal in text for signal in ("proxyerror", "connect", "timed out", "10061")):
        return False
    return True


def _split_oversized_section(section: str) -> list[str]:
    parts = []
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
    sections = []
    current_lines = []

    for line in text.splitlines():
        if SECTION_HEADER_PATTERN.match(line.strip()) and current_lines:
            sections.append("\n".join(current_lines).strip())
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append("\n".join(current_lines).strip())

    return [section for section in sections if section]


def _split_message(text: str) -> list[str]:
    sections = _extract_sections(text)
    if not sections:
        return _split_oversized_section(text)

    parts = []
    current_part = ""

    for section in sections:
        if len(section) > MAX_CHARS:
            if current_part:
                parts.append(current_part.strip())
                current_part = ""
            parts.extend(_split_oversized_section(section))
            continue

        candidate = f"{current_part}\n\n{section}".strip() if current_part else section
        if len(candidate) <= MAX_CHARS:
            current_part = candidate
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = section

    if current_part:
        parts.append(current_part.strip())

    return parts


def _send_single(text: str):
    from_number, to_number = _from_number(), _to_number()
    client = _build_client()
    if _dev_mode() or client is None or not from_number or not to_number:
        print(f"\n[WhatsApp DEV]\n{text}\n{'=' * 40}")
        return

    try:
        message = client.messages.create(from_=from_number, to=to_number, body=text)
        print(f"[WhatsApp] Sent: {message.sid}")
    except Exception as exc:
        print(f"[WhatsApp] Send error: {exc}")
        if not _should_retry_send(exc):
            return
        try:
            time.sleep(SEND_RETRY_DELAY_SECONDS)
            client.messages.create(from_=from_number, to=to_number, body=text)
        except Exception as retry_exc:
            print(f"[WhatsApp] Retry failed: {retry_exc}")


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
    from_number, to_number = _from_number(), _to_number()
    client = _build_client()
    if _dev_mode() or client is None or not from_number or not to_number:
        return "timeout"

    deadline = time.time() + (timeout_minutes * 60)
    last_check_sid = None

    while time.time() < deadline:
        try:
            messages = client.messages.list(to=from_number, from_=to_number, limit=1)
            if messages:
                message = messages[0]
                if message.sid != last_check_sid:
                    last_check_sid = message.sid
                    return message.body.strip()
        except Exception as exc:
            print(f"[WhatsApp] Poll error: {exc}")

        time.sleep(30)

    return "timeout"
