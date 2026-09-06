from twilio.rest import Client
from app.core.config import settings

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_whatsapp_message(to_number: str, body: str) -> str:
    msg = client.messages.create(
        from_=settings.TWILIO_WHATSAPP_NUMBER,
        to=to_number,
        body=body
    )
    return msg.sid
