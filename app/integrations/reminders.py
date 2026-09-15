from datetime import datetime
from zoneinfo import ZoneInfo

from pymongo import MongoClient
from bson import ObjectId

from app.core.config import settings

TZ = ZoneInfo(settings.SCHEDULER_TIMEZONE)

_client: MongoClient | None = None


def _get_collection():
    if not settings.MONGO_URL:
        return None
    global _client
    if _client is None:
        _client = MongoClient(
            settings.MONGO_URL,
            serverSelectionTimeoutMS=3000,
        )
    return _client[settings.MONGO_DB_NAME]["reminders"]


def create_reminder(text: str, due_at: datetime) -> dict:
    coll = _get_collection()
    if coll is None:
        raise RuntimeError("MONGO_URL is not configured.")

    due_ist = due_at.astimezone(TZ) if due_at.tzinfo else due_at.replace(tzinfo=TZ)
    doc = {
        "text": text,
        "due_at": due_ist.isoformat(),
        "status": "pending",
        "created_at": datetime.now(TZ).isoformat(),
    }
    result = coll.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


def get_due_reminders(limit: int = 25) -> list[dict]:
    coll = _get_collection()
    if coll is None:
        return []

    now_iso = datetime.now(TZ).isoformat()
    cursor = coll.find(
        {"status": "pending", "due_at": {"$lte": now_iso}},
    ).sort("due_at", 1).limit(limit)

    return [
        {**doc, "_id": str(doc["_id"])}
        for doc in cursor
    ]


def mark_reminder_sent(reminder_id: str) -> None:
    coll = _get_collection()
    if coll is None:
        return
    coll.update_one(
        {"_id": ObjectId(reminder_id)},
        {"$set": {
            "status": "sent",
            "sent_at": datetime.now(TZ).isoformat(),
        }},
    )
