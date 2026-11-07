import json
from typing import Optional, List, Dict
import httpx
from twilio.rest import Client
from app.core.config import settings

_client: Optional[Client] = None
PERSONAL_CLIENT_BRIDGE_URL = "http://127.0.0.1:5001"
_PAID_BURST_CONTENT_SID: Optional[str] = None


def get_twilio_client() -> Optional[Client]:
    """Lazily initialize Twilio client if credentials are configured."""
    global _client
    if _client is None:
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client


def send_whatsapp_message(to_number: str, body: str) -> str:
    """Send standard WhatsApp text message via Twilio."""
    client = get_twilio_client()
    if not client or not settings.TWILIO_WHATSAPP_NUMBER:
        print("[twilio_service] Twilio is not configured; skipping Twilio send.")
        return "mock_twilio_skipped"

    msg = client.messages.create(
        from_=settings.TWILIO_WHATSAPP_NUMBER,
        to=to_number,
        body=body
    )
    return msg.sid


def get_or_create_paid_burst_content_template() -> Optional[str]:
    """Get or create Twilio Content API template for the 9 AM Paid-Burst Quick Reply button."""
    global _PAID_BURST_CONTENT_SID
    if _PAID_BURST_CONTENT_SID:
        return _PAID_BURST_CONTENT_SID

    client = get_twilio_client()
    if not client:
        return None

    try:
        # Check if template already exists
        contents = client.content.v1.contents.list(limit=20)
        for item in contents:
            if item.friendly_name == "paid_burst_9am_quick_reply":
                _PAID_BURST_CONTENT_SID = item.sid
                return _PAID_BURST_CONTENT_SID

        # Create quick-reply content template
        created = client.content.v1.contents.create(
            friendly_name="paid_burst_9am_quick_reply",
            language="en",
            types={
                "twilio/quick-reply": {
                    "body": "🌅 Good morning Haricharan!\nTime for your 9:00 AM daily check-in.\n\nReady to crush today's goals?\nTap below to join today's Paid-Burst session! 🚀",
                    "actions": [
                        {
                            "title": "join paid-burst",
                            "id": "join_paid_burst"
                        }
                    ]
                }
            }
        )
        _PAID_BURST_CONTENT_SID = created.sid
        return _PAID_BURST_CONTENT_SID
    except Exception as e:
        print(f"[twilio_service] Content Template check/create skipped: {e}")
        return None


async def send_whatsapp_interactive_button(
    to_number: str,
    body: str,
    button_text: str = "join paid-burst",
    title: str = "⚡ Paid-Burst Morning Sprint",
    footer: str = "Tap to join"
) -> str:
    """Send interactive WhatsApp button message.

    Attempts delivery via:
    1. Local personal_client bridge (whatsapp-web.js Buttons / Poll) if available.
    2. Twilio Content API (quick-reply template).
    3. Twilio WhatsApp formatted message with 1-tap reply action.
    """
    # 1. Try personal_client bridge if active
    try:
        async with httpx.AsyncClient(timeout=2.0) as http_client:
            resp = await http_client.post(
                f"{PERSONAL_CLIENT_BRIDGE_URL}/send-button",
                json={
                    "to": to_number,
                    "body": body,
                    "buttonText": button_text,
                    "title": title,
                    "footer": footer,
                }
            )
            if resp.status_code == 200:
                print("[twilio_service] Sent interactive button via personal_client bridge.")
                return resp.json().get("id", "personal_client_ok")
    except Exception:
        pass  # Fall back to Twilio

    # 2. Try Twilio Content API template
    content_sid = get_or_create_paid_burst_content_template()
    client = get_twilio_client()
    if content_sid and client and settings.TWILIO_WHATSAPP_NUMBER:
        try:
            msg = client.messages.create(
                from_=settings.TWILIO_WHATSAPP_NUMBER,
                to=to_number,
                content_sid=content_sid
            )
            return msg.sid
        except Exception as e:
            print(f"[twilio_service] Twilio Content API send failed: {e}. Falling back to formatted message.")

    # 3. Fallback: formatted message with quick-tap quote and bold directive
    fallback_body = (
        f"{body}\n\n"
        f"┌───────────────────────────────┐\n"
        f"│  🔘 *[{button_text.upper()}]*  │\n"
        f"└───────────────────────────────┘\n\n"
        f"👉 _Tap or reply: *{button_text}*_"
    )
    return send_whatsapp_message(to_number=to_number, body=fallback_body)
