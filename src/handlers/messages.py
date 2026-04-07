"""
Pending session store
─────────────────────
Data structure: dict[user_id → (links, timestamp)]
  - O(1) get/set/delete per user
  - TTL enforced on read: if the entry is older than SESSION_TTL seconds
    it is discarded, preventing memory leaks from users who never pick quality.
"""
import os
import tempfile
import time
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import settings
from helper.link_parser import extract_links
from ui.keyboards import quality_keyboard
from ui.templates import Msg

logger = logging.getLogger(__name__)

# pending[user_id] = (links: list[str], timestamp: float)
_pending: dict[int, tuple[list[str], float]] = {}


def _store_pending(user_id: int, links: list[str]) -> None:
    _pending[user_id] = (links, time.monotonic())


def pop_pending(user_id: int) -> list[str] | None:
    """Pop pending links for a user. Returns None if missing or expired."""
    entry = _pending.pop(user_id, None)
    if entry is None:
        return None
    links, timestamp = entry
    if time.monotonic() - timestamp > settings.session_ttl:
        logger.info("Session for user %d expired", user_id)
        return None
    return links


# ── Handlers ─────────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a plain-text message: extract TikTok links and ask for quality."""
    text = update.message.text or ""
    links = extract_links(text)
    if not links:
        await update.message.reply_text(Msg.NO_LINKS_FOUND)
        return

    _store_pending(update.effective_user.id, links)
    await update.message.reply_text(
        Msg.links_found(len(links), source="message"),
        parse_mode="Markdown",
        reply_markup=quality_keyboard(),
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a .txt file upload: extract links inside and ask for quality."""
    doc = update.message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".txt"):
        await update.message.reply_text(Msg.NOT_A_TXT_FILE, parse_mode="Markdown")
        return

    if doc.file_size and doc.file_size > 5 * 1024 * 1024:
        await update.message.reply_text(Msg.FILE_TOO_LARGE)
        return

    file = await context.bot.get_file(doc.file_id)
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await file.download_to_drive(tmp_path)
        with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    links = extract_links(content)
    if not links:
        await update.message.reply_text(Msg.NO_LINKS_IN_FILE)
        return

    _store_pending(update.effective_user.id, links)
    await update.message.reply_text(
        Msg.links_found(len(links), source="file"),
        parse_mode="Markdown",
        reply_markup=quality_keyboard(),
    )
