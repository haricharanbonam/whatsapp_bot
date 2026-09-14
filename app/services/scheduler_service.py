from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.twilio_service import send_whatsapp_message
from app.core.config import settings
from app.integrations.calendar import fetch_daily_events, format_events_message
from app.services.leetcode_service import fetch_activity, fetch_daily_question

scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)

async def scheduled_daily_tasks_job():
    try:
        events = fetch_daily_events()
        body = format_events_message(events)
        send_whatsapp_message(
            to_number=settings.MY_WHATSAPP_NUMBER,
            body=body
        )
    except Exception as e:
        print(f"Scheduler error: {e}")

def format_daily_challenge_message(daily: dict) -> str:
    topics = ", ".join(daily.get("topics") or []) or "General"
    return (
        f"🔥 Daily LeetCode Challenge · {daily.get('date')}\n\n"
        f"Q{daily.get('question_number')} · {daily.get('title')}\n"
        f"Difficulty: {daily.get('difficulty')}\n"
        f"Topics: {topics}\n\n"
        f"👉 Solve it: {daily.get('link')}\n\n"
        f"15 minutes a day keeps the rust away. Let's go! 🚀"
    )

REMINDER_MESSAGES = {
    "noon": (
        "🌤️ Broo, still 0 solves today! A quick 10-minute warm-up before lunch "
        "keeps the streak alive. Just one problem, you got this! 💪"
    ),
    "evening": (
        "⏰ It's 5 PM and no LeetCode yet! Gift yourself ONE problem before the "
        "day slips away. Green square > Netflix. 🔥"
    ),
    "night": (
        "🌙 Last call bro — not a single solve today! 15 minutes, one problem, "
        "save that green square. You got this. 💯"
    ),
}

async def send_daily_challenge():
    try:
        daily = await fetch_daily_question()
        body = format_daily_challenge_message(daily)
        send_whatsapp_message(
            to_number=settings.MY_WHATSAPP_NUMBER,
            body=body
        )
    except Exception as e:
        print(f"LeetCode daily job error: {e}")

async def send_solve_reminder(slot: str):
    username = settings.LEETCODE_USERNAME
    if not username:
        print("LEETCODE_USERNAME not set, skipping LeetCode reminder.")
        return
    try:
        activity = await fetch_activity(username)
        if not activity["active_today"]:
            send_whatsapp_message(
                to_number=settings.MY_WHATSAPP_NUMBER,
                body=REMINDER_MESSAGES[slot]
            )
    except Exception as e:
        print(f"LeetCode reminder job error: {e}")

def start_scheduler():
    scheduler.add_job(
        scheduled_daily_tasks_job,
        "cron",
        hour=9,
        minute=0,
        id="calendar_daily_tasks",
        replace_existing=True,
    )
    scheduler.add_job(
        send_daily_challenge,
        "cron",
        hour=6,
        minute=0,
        id="leetcode_daily_challenge",
        replace_existing=True,
    )
    scheduler.add_job(
        send_solve_reminder,
        "cron",
        hour=12,
        minute=0,
        args=["noon"],
        id="leetcode_reminder_noon",
        replace_existing=True,
    )
    scheduler.add_job(
        send_solve_reminder,
        "cron",
        hour=17,
        minute=0,
        args=["evening"],
        id="leetcode_reminder_evening",
        replace_existing=True,
    )
    scheduler.add_job(
        send_solve_reminder,
        "cron",
        hour=22,
        minute=0,
        args=["night"],
        id="leetcode_reminder_night",
        replace_existing=True,
    )
    scheduler.start()