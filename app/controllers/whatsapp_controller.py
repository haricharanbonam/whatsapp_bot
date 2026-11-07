from fastapi import APIRouter, Form, Response, Query
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse

from app.services.ai_service import generate_chat_response
from app.services.scheduler_service import scheduled_daily_9am_paid_burst_job
from app.integrations.technical_questions import (
    get_daily_mern_question,
    get_daily_sql_question,
    format_mern_question_message,
    format_sql_question_message,
)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


@router.post("/webhook")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    """Twilio WhatsApp inbound webhook."""
    user_msg = Body.strip()
    reply_text = await generate_chat_response(user_text=user_msg, user_id=From)

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(content=str(twiml), media_type="application/xml")


class PersonalAIMessage(BaseModel):
    prompt: str
    sender: str


@router.post("/personal")
async def handle_personal_ai(payload: PersonalAIMessage):
    """WhatsApp Web personal client bridge webhook."""
    reply = await generate_chat_response(user_text=payload.prompt, user_id=payload.sender)
    return {"reply": reply}


@router.post("/trigger-9am-burst")
async def trigger_9am_burst():
    """Manual trigger to test sending the 9:00 AM Paid-Burst interactive button message."""
    await scheduled_daily_9am_paid_burst_job()
    return {"status": "success", "message": "Triggered 9 AM Paid-Burst button dispatch."}


@router.get("/daily-questions")
def get_daily_questions():
    """Fetch today's MERN and SQL questions."""
    mern_q = get_daily_mern_question()
    sql_q = get_daily_sql_question()
    return {
        "mern": {
            "data": mern_q,
            "formatted": format_mern_question_message(mern_q),
        },
        "sql": {
            "data": sql_q,
            "formatted": format_sql_question_message(sql_q),
        }
    }
