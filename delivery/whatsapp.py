"""Backwards-compatibility shim. Delivery moved to Telegram; this module
re-exports the same names so any lingering `from delivery.whatsapp import …`
continues to work. New code should import from `delivery.telegram` directly.
"""

from delivery.telegram import (  # noqa: F401
    TelegramDeliveryError as WhatsAppDeliveryError,
    send_digest,
    send_message,
    wait_for_reply,
)
