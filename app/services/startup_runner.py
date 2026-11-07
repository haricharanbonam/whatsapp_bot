from app.services.scheduler_service import (
    scheduled_daily_9am_paid_burst_job,
    send_daily_challenge,
    send_solve_reminder,
    send_daily_mern_job,
    send_daily_sql_job,
)


async def run_once_updates():
    """Run initial test checks once on startup if needed."""
    try:
        await scheduled_daily_9am_paid_burst_job()
    except Exception as e:
        print(f"[startup_runner] Notice: {e}")
