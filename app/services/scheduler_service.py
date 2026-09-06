from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.twilio_service import send_whatsapp_message
from app.core.config import settings

scheduler = AsyncIOScheduler()

async def scheduled_ping_job():
    try:
        send_whatsapp_message(
            to_number=settings.MY_WHATSAPP_NUMBER,
            body="[Cron Ping]: Scheduled alert from your bot."
        )
    except Exception as e:
        print(f"Cron error: {e}")

def start_scheduler():
    # Runs every 2 hours (adjust as needed)
    scheduler.add_job(scheduled_ping_job, "interval", hours=2, id="cron_ping", replace_existing=True)
    scheduler.start()
