"""
_user_store_json.py — JSON file backend for user tracking.

Do not import this directly. Import from user_store.py instead.

Thread safety: asyncio.Lock — safe for concurrent bot handlers.
Data survives Docker rebuild via a mounted host volume.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from config.settings import settings

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_raw() -> dict:
    path = settings.users_file
    if not os.path.exists(path):
        return {"users": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read users file (%s), starting fresh: %s", path, exc)
        return {"users": {}}


def _save_raw(data: dict) -> None:
    path = settings.users_file
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)  # atomic write — no partial file on crash


async def record_user(user_id: int, username: str | None, first_name: str) -> None:
    """Create or update a user record. Increments download_count on each call."""
    async with _lock:
        data = _load_raw()
        key = str(user_id)
        now = _now()
        if key not in data["users"]:
            data["users"][key] = {
                "id": user_id,
                "username": username or "",
                "first_name": first_name,
                "first_seen": now,
                "last_seen": now,
                "download_count": 0,
            }
            logger.info("New user registered: %s (%s)", first_name, user_id)
        else:
            data["users"][key]["username"] = username or ""
            data["users"][key]["first_name"] = first_name
            data["users"][key]["last_seen"] = now
        data["users"][key]["download_count"] += 1
        _save_raw(data)


async def get_stats() -> dict:
    """Return summary stats dict."""
    async with _lock:
        data = _load_raw()
        users = data["users"]
        total_users = len(users)
        total_downloads = sum(u["download_count"] for u in users.values())
        return {
            "total_users": total_users,
            "total_downloads": total_downloads,
        }


async def get_all_users() -> list[dict]:
    """Return all user records sorted by first_seen."""
    async with _lock:
        data = _load_raw()
        return sorted(data["users"].values(), key=lambda u: u["first_seen"])


async def get_lang(user_id: int) -> str:
    async with _lock:
        data = _load_raw()
        return data["users"].get(str(user_id), {}).get("lang", "en")


async def set_lang(user_id: int, lang: str) -> None:
    async with _lock:
        data = _load_raw()
        key = str(user_id)
        if key not in data["users"]:
            data["users"][key] = {"id": user_id, "lang": lang}
        else:
            data["users"][key]["lang"] = lang
        _save_raw(data)
