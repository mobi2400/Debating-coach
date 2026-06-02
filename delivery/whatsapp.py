import os
import time

from dotenv import load_dotenv

try:
    from twilio.rest import Client
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    Client = None

load_dotenv()

MAX_CHARS = 1500


def _account_sid() -> str | None:
    return os.getenv("TWILIO_ACCOUNT_SID")


def _auth_token() -> str | None:
    return os.getenv("TWILIO_AUTH_TOKEN")


def _from_number() -> str | None:
    return os.getenv("TWILIO_WHATSAPP_FROM")


def _to_number() -> str | None:
    return os.getenv("YOUR_WHATSAPP_NUMBER")


def _dev_mode() -> bool:
    return os.getenv("DEV_MODE", "false").lower() == "true"


def _build_client():
    sid, token = _account_sid(), _auth_token()
    if Client is None or not sid or not token:
        return None
    return Client(sid, token)


def _split_message(text: str) -> list[str]:
    parts = []
    while len(text) > MAX_CHARS:
        split_at = text.rfind("\n", 0, MAX_CHARS)
        if split_at == -1:
            split_at = MAX_CHARS
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        parts.append(text)
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
        try:
            time.sleep(3)
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
