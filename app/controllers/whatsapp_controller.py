from fastapi import APIRouter, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from app.services.ai_service import generate_chat_response

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

@router.post("/webhook")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    user_msg = Body.strip()
    reply_text = await generate_chat_response(user_text=user_msg, user_id=From)

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(content=str(twiml), media_type="application/xml")



from pydantic import BaseModel

class PersonalAIMessage(BaseModel):
    prompt: str
    sender: str

@router.post("/personal")
async def handle_personal_ai(payload: PersonalAIMessage):
    # Reuses your existing ai_service.py logic!
    reply = await generate_chat_response(user_text=payload.prompt, user_id=payload.sender)
    return {"reply": reply}