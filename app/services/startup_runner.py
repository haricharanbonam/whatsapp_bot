from app.services.scheduler_service import (
    scheduled_daily_tasks_job,
    send_daily_challenge,
    send_solve_reminder,
)


async def run_once_updates():
    """Run calendar, LeetCode daily, and LeetCode streak checks once on startup.

    Intended for testing regardless of the scheduled times.
    """
    await scheduled_daily_tasks_job()
    await send_daily_challenge()
    await send_solve_reminder("noon")