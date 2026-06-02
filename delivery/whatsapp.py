import os
import time

from dotenv import load_dotenv

try:
    from twilio.rest import Client
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    Client = None

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_FROM")
TO_NUMBER = os.getenv("YOUR_WHATSAPP_NUMBER")
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

MAX_CHARS = 4000


def _build_client():
    if Client is None or not ACCOUNT_SID or not AUTH_TOKEN:
        return None
    return Client(ACCOUNT_SID, AUTH_TOKEN)


client = _build_client()


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
    if DEV_MODE or client is None or not FROM_NUMBER or not TO_NUMBER:
        print(f"\n[WhatsApp DEV]\n{text}\n{'=' * 40}")
        return

    try:
        message = client.messages.create(from_=FROM_NUMBER, to=TO_NUMBER, body=text)
        print(f"[WhatsApp] Sent: {message.sid}")
    except Exception as exc:
        print(f"[WhatsApp] Send error: {exc}")
        try:
            time.sleep(3)
            client.messages.create(from_=FROM_NUMBER, to=TO_NUMBER, body=text)
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
