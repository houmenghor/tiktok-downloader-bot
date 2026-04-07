"""
user_store.py — persistent user registry.

Auto-selects backend based on environment:
  - MONGO_URI is set  → MongoDB Atlas  (use on Render / cloud)
  - MONGO_URI not set → JSON file      (use on local / Ubuntu server with Docker volume)

Import only from this module — never import the backends directly.
"""
import os

# ── Backend selection ─────────────────────────────────────────────────────────
if os.getenv("MONGO_URI"):
    from helper.user_store_mongo import record_user, get_stats, get_all_users, get_lang, set_lang  # noqa: F401
else:
    from helper._user_store_json import record_user, get_stats, get_all_users, get_lang, set_lang  # noqa: F401
