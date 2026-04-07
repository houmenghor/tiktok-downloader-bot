"""
TikTok Downloader Telegram Bot

Flow:
  Single link  → user sends URL → bot shows [1080p] [1440p] → queued → video sent back
  Batch (.txt) → user uploads file → bot shows [1080p] [1440p] → all links queued → videos sent back
"""
import logging
import os
import re
import tempfile

from telegram import (
    Document,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from downloader import cleanup_files, download_video
from queue_manager import DownloadJob, DownloadQueue

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
download_queue = DownloadQueue(max_workers=config.MAX_WORKERS)

# Pending quality selections: user_id → list of URLs
pending: dict[int, list[str]] = {}

TIKTOK_RE = re.compile(
    r"https?://(?:www\.|vm\.|vt\.)?tiktok\.com/\S+",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def quality_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 1080p", callback_data="quality_1080p"),
            InlineKeyboardButton("🎥 1440p", callback_data="quality_1440p"),
        ]
    ])


def extract_links(text: str) -> list[str]:
    return TIKTOK_RE.findall(text)


async def process_job(job: DownloadJob) -> None:
    """Called by queue worker for each job."""
    app: Application = job.callback.__self__  # type: ignore[attr-defined]
    bot = app.bot

    status_msg: Message = await bot.send_message(
        chat_id=job.chat_id,
        text=f"⏬ Downloading {job.label} ({job.quality})...",
    )

    try:
        output_dir = os.path.join(config.DOWNLOAD_DIR, str(job.user_id))
        files = await download_video(job.url, job.quality, output_dir)

        if len(files) == 1:
            await bot.send_video(
                chat_id=job.chat_id,
                video=open(files[0], "rb"),
                caption=f"✅ {job.label} ({job.quality})",
                supports_streaming=True,
            )
        else:
            await bot.send_message(
                chat_id=job.chat_id,
                text=f"📦 {job.label} is large — sending in {len(files)} parts.",
            )
            for idx, part in enumerate(files, start=1):
                await bot.send_video(
                    chat_id=job.chat_id,
                    video=open(part, "rb"),
                    caption=f"✅ {job.label} — Part {idx}/{len(files)} ({job.quality})",
                    supports_streaming=True,
                )

        cleanup_files(files)

    except Exception as exc:
        logger.exception("Job %s failed: %s", job.job_id, exc)
        await bot.send_message(
            chat_id=job.chat_id,
            text=f"❌ Failed to download {job.label}.\nError: {exc}",
        )
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *TikTok Downloader Bot*\n\n"
        "Send me a TikTok link *or* upload a *.txt* file with one link per line.\n"
        "I'll ask you for the quality and then download everything for you.\n\n"
        "Commands:\n"
        "/start — show this message\n"
        "/queue — show current queue size",
        parse_mode="Markdown",
    )


async def cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    size = download_queue.qsize()
    await update.message.reply_text(
        f"📋 Jobs currently in queue: *{size}*",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Message handlers
# ---------------------------------------------------------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages — look for TikTok links."""
    text = update.message.text or ""
    links = extract_links(text)
    if not links:
        await update.message.reply_text(
            "⚠️ No TikTok links found. Please send a valid TikTok URL."
        )
        return

    pending[update.effective_user.id] = links
    count = len(links)
    noun = "link" if count == 1 else "links"
    await update.message.reply_text(
        f"Found *{count}* {noun}. Choose download quality:",
        parse_mode="Markdown",
        reply_markup=quality_keyboard(),
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle .txt file uploads containing TikTok links."""
    doc: Document = update.message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".txt"):
        await update.message.reply_text("⚠️ Please upload a plain *.txt* file.", parse_mode="Markdown")
        return

    if doc.file_size and doc.file_size > 5 * 1024 * 1024:
        await update.message.reply_text("⚠️ File is too large. Max 5 MB for link list.")
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
        await update.message.reply_text("⚠️ No TikTok links found in the file.")
        return

    pending[update.effective_user.id] = links
    count = len(links)
    await update.message.reply_text(
        f"📄 Found *{count}* link(s) in the file. Choose download quality:",
        parse_mode="Markdown",
        reply_markup=quality_keyboard(),
    )


# ---------------------------------------------------------------------------
# Callback query handler (quality selection)
# ---------------------------------------------------------------------------

async def handle_quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    _quality_map = {"quality_1080p": "1080p", "quality_1440p": "1440p"}
    quality = _quality_map.get(query.data, "1080p")

    links = pending.pop(user_id, None)
    if not links:
        await query.edit_message_text("⚠️ Session expired. Please send the link(s) again.")
        return

    total = len(links)
    for idx, url in enumerate(links, start=1):
        label = f"Link {idx}/{total}" if total > 1 else "Video"
        job = DownloadJob(
            job_id=DownloadJob.make_id(),
            user_id=user_id,
            chat_id=chat_id,
            url=url,
            quality=quality,
            label=label,
            callback=process_job,  # type: ignore[arg-type]
        )
        position = await download_queue.add_job(job)

    noun = "link" if total == 1 else "links"
    await query.edit_message_text(
        f"✅ *{total}* {noun} added to queue at *{quality}*.\n"
        f"Queue size: {position} job(s). I'll send videos as they finish.",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def post_init(application: Application) -> None:
    await download_queue.start()


async def post_shutdown(application: Application) -> None:
    await download_queue.stop()


def main() -> None:
    if not config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set. Check your .env file.")

    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("queue", cmd_queue))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), handle_document))
    app.add_handler(CallbackQueryHandler(handle_quality_callback, pattern=r"^quality_"))

    logger.info("Bot started. Polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
