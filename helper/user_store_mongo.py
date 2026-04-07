"""
user_store_mongo.py — MongoDB Atlas backend for user tracking.

Used automatically when MONGO_URI is set in the environment.
Drop-in replacement for user_store.py — same public API.

Collection schema (one document per user):
{
  "_id": <telegram_user_id>,
  "username": "john",
  "first_name": "John",
  "first_seen": <datetime>,
  "last_seen": <datetime>,
  "download_count": 5
}
"""
import logging
from datetime import datetime, timezone

import certifi
from motor.motor_asyncio import AsyncIOMotorClient

from config.settings import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


def _db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri, tlsCAFile=certifi.where())
    return _client["tiktok_bot"]["users"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def record_user(user_id: int, username: str | None, first_name: str) -> None:
    col = _db()
    now = _now()
    await col.update_one(
        {"_id": user_id},
        {
            "$set": {
                "username": username or "",
                "first_name": first_name,
                "last_seen": now,
            },
            "$setOnInsert": {
                "first_seen": now,
            },
            "$inc": {"download_count": 1},
        },
        upsert=True,
    )


async def get_stats() -> dict:
    col = _db()
    total_users = await col.count_documents({})
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$download_count"}}}]
    result = await col.aggregate(pipeline).to_list(1)
    total_downloads = result[0]["total"] if result else 0
    return {"total_users": total_users, "total_downloads": total_downloads}


async def get_all_users() -> list[dict]:
    col = _db()
    cursor = col.find({}, {"_id": 0}).sort("first_seen", 1)
    return await cursor.to_list(None)


async def get_lang(user_id: int) -> str:
    col = _db()
    doc = await col.find_one({"_id": user_id}, {"lang": 1})
    return (doc.get("lang") or "en") if doc else "en"


async def set_lang(user_id: int, lang: str) -> None:
    col = _db()
    await col.update_one(
        {"_id": user_id},
        {"$set": {"lang": lang}},
        upsert=True,
    )
