from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.twilio_service import send_whatsapp_message, send_whatsapp_interactive_button
from app.core.config import settings
from app.integrations.calendar import fetch_daily_events, format_events_message
from app.integrations.reminders import get_due_reminders, mark_reminder_sent
from app.services.leetcode_service import fetch_activity, fetch_daily_question
from app.integrations.technical_questions import (
    get_daily_mern_question,
    get_daily_sql_question,
    format_mern_question_message,
    format_sql_question_message,
)

scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)


async def scheduled_daily_9am_paid_burst_job():
    """9:00 AM Daily Briefing with interactive 'join paid-burst' button."""
    try:
        events = fetch_daily_events()
        calendar_summary = format_events_message(events)
    except Exception as e:
        print(f"[scheduler] Calendar fetch note: {e}")
        calendar_summary = "Calendar events unavailable right now."

    body = (
        "🌅 *Good Morning Haricharan!*\n"
        "It's 9:00 AM — time to start today's focus block.\n\n"
        f"📅 *Today's Schedule:*\n{calendar_summary}\n\n"
        "🔥 *Today's Grind:*\n"
        "• LeetCode Daily\n"
        "• MERN Deep Dive\n"
        "• SQL Query Challenge\n\n"
        "Tap the button below to lock in your morning Paid-Burst session! 👇"
    )

    try:
        await send_whatsapp_interactive_button(
            to_number=settings.MY_WHATSAPP_NUMBER,
            body=body,
            button_text="join paid-burst",
            title="⚡ Paid-Burst Morning Sprint",
            footer="Tap below to check in"
        )
        print("[scheduler] 9 AM Paid-Burst button message sent successfully.")
    except Exception as e:
        print(f"[scheduler] Error sending 9 AM Paid-Burst message: {e}")


async def send_daily_mern_job():
    """Daily MERN technical challenge."""
    try:
        q = get_daily_mern_question()
        body = format_mern_question_message(q)
        send_whatsapp_message(
            to_number=settings.MY_WHATSAPP_NUMBER,
            body=body
        )
        print("[scheduler] Daily MERN question sent.")
    except Exception as e:
        print(f"[scheduler] MERN job error: {e}")


async def send_daily_sql_job():
    """Daily SQL query challenge."""
    try:
        q = get_daily_sql_question()
        body = format_sql_question_message(q)
        send_whatsapp_message(
            to_number=settings.MY_WHATSAPP_NUMBER,
            body=body
        )
        print("[scheduler] Daily SQL query sent.")
    except Exception as e:
        print(f"[scheduler] SQL job error: {e}")


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


async def check_and_send_reminders():
    try:
        reminders = get_due_reminders()
        for reminder in reminders:
            send_whatsapp_message(
                to_number=settings.MY_WHATSAPP_NUMBER,
                body=f"⏰ Reminder: {reminder['text']}"
            )
            mark_reminder_sent(reminder["_id"])
    except Exception as e:
        print(f"Reminder poller error: {e}")


def start_scheduler():
    # 09:00 AM: Morning agenda + interactive Paid-Burst button
    scheduler.add_job(
        scheduled_daily_9am_paid_burst_job,
        "cron",
        hour=9,
        minute=0,
        id="daily_9am_paid_burst",
        replace_existing=True,
    )
    # 06:00 AM: LeetCode Daily Challenge
    scheduler.add_job(
        send_daily_challenge,
        "cron",
        hour=6,
        minute=0,
        id="leetcode_daily_challenge",
        replace_existing=True,
    )
    # 10:30 AM: Daily MERN Question
    scheduler.add_job(
        send_daily_mern_job,
        "cron",
        hour=10,
        minute=30,
        id="daily_mern_question",
        replace_existing=True,
    )
    # 14:00 PM: Daily SQL Query Challenge
    scheduler.add_job(
        send_daily_sql_job,
        "cron",
        hour=14,
        minute=0,
        id="daily_sql_challenge",
        replace_existing=True,
    )
    # LeetCode streak reminders
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
    # Reminder interval poller
    scheduler.add_job(
        check_and_send_reminders,
        "interval",
        minutes=settings.REMINDER_POLL_INTERVAL_MINUTES,
        id="reminder_poller",
        replace_existing=True,
    )
    scheduler.start()


# Backward-compatibility alias
scheduled_daily_tasks_job = scheduled_daily_9am_paid_burst_job

