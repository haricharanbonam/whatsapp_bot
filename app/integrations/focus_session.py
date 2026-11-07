"""Focus Session & Paid-Burst Integration.

Tracks Haricharan's daily morning Paid-Burst check-ins, focus streaks,
and session timestamps in MongoDB.
"""

from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Optional

from pymongo import MongoClient
from app.core.config import settings

TZ = ZoneInfo(settings.SCHEDULER_TIMEZONE)
_client: MongoClient | None = None


def _get_collection():
    if not settings.MONGO_URL:
        return None
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=3000)
    return _client[settings.MONGO_DB_NAME]["focus_sessions"]


def record_paid_burst_checkin(user_id: str = "Haricharan", notes: str = "") -> dict:
    """Record a Paid-Burst session check-in and calculate current streak."""
    now = datetime.now(TZ)
    today_str = now.strftime("%Y-%m-%d")

    coll = _get_collection()
    if coll is None:
        return {
            "status": "active",
            "date": today_str,
            "time": now.strftime("%I:%M %p"),
            "streak": 1,
            "message": "Paid-Burst logged locally (MongoDB not configured)."
        }

    # Check if already checked in today
    existing = coll.find_one({"user_id": user_id, "date": today_str})
    if existing:
        return {
            "status": "already_checked_in",
            "date": today_str,
            "time": existing.get("checked_in_at_time", now.strftime("%I:%M %p")),
            "streak": existing.get("streak", 1),
            "is_duplicate": True,
        }

    # Calculate streak from previous check-ins
    recent = list(coll.find({"user_id": user_id}).sort("date", -1).limit(30))
    streak = 1
    if recent:
        last_date = datetime.strptime(recent[0]["date"], "%Y-%m-%d").date()
        today_date = now.date()
        diff = (today_date - last_date).days
        if diff == 1:
            streak = recent[0].get("streak", 1) + 1
        elif diff == 0:
            streak = recent[0].get("streak", 1)
        else:
            streak = 1

    doc = {
        "user_id": user_id,
        "date": today_str,
        "checked_in_at": now.isoformat(),
        "checked_in_at_time": now.strftime("%I:%M %p"),
        "streak": streak,
        "notes": notes,
        "type": "paid-burst"
    }
    coll.insert_one(doc)
    return {
        "status": "success",
        "date": today_str,
        "time": now.strftime("%I:%M %p"),
        "streak": streak,
        "is_duplicate": False,
    }


def get_paid_burst_stats(user_id: str = "Haricharan") -> dict:
    """Get total check-ins and current streak for user."""
    coll = _get_collection()
    if coll is None:
        return {"total_sessions": 0, "current_streak": 0}

    total = coll.count_documents({"user_id": user_id})
    latest = coll.find_one({"user_id": user_id}, sort=[("date", -1)])
    current_streak = latest.get("streak", 0) if latest else 0

    return {
        "total_sessions": total,
        "current_streak": current_streak,
        "last_session_date": latest.get("date") if latest else None
    }
