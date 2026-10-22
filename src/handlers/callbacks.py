import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.messages import pop_pending, store_pending_save, pop_pending_save
from src.queue_manager import DownloadJob
from helper.user_store import record_user, get_lang
from ui.keyboards import folder_keyboard
from ui.templates import Msg

logger = logging.getLogger(__name__)


async def handle_quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User pressed a quality button.

    - Single link  → enqueue immediately (send to chat).
    - Batch links  → show folder picker (save locally, no upload).
    """
    query = update.callback_query
    await query.answer()

    from src.bot import download_queue, process_job  # late import — avoids circular dep

    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    lang = await get_lang(user_id)
    msg = Msg(lang)
    _quality_map = {"quality_1080p": "1080p", "quality_1440p": "1440p", "quality_2160p": "2160p", "quality_audio": "audio"}
    quality = _quality_map.get(query.data, "1080p")

    res = pop_pending(user_id, kind="video")
    if not res:
        await query.edit_message_text(msg.SESSION_EXPIRED)
        return
    links, source = res

    await record_user(user_id, user.username, user.first_name or "")

    # Always enqueue directly to send to Telegram chat
    default_label = "Audio" if quality == "audio" else "Video"
    for idx, url in enumerate(links, start=1):
        label = f"Link {idx}/{len(links)}" if len(links) > 1 else default_label
        job = DownloadJob(
            user_id=user_id,
            chat_id=chat_id,
            url=url,
            quality=quality,
            label=label,
            callback=process_job,
            save_locally=False,
        )
        await download_queue.add_job(job)

    await query.edit_message_text(
        msg.queued(len(links), quality, len(links)),
        parse_mode="Markdown",
    )


async def handle_photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User pressed a photo format button (photos, audio, or photos+audio).

    All links are enqueued immediately and sent directly to the Telegram chat.
    """
    query = update.callback_query
    await query.answer()

    from src.bot import download_queue, process_job

    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    lang = await get_lang(user_id)
    msg = Msg(lang)

    _photo_map = {
        "photo_photos": ("photo", "Photos"),
        "photo_audio": ("audio", "Audio"),
        "photo_both": ("photo_both", "Photos + Audio"),
    }
    format_choice, label = _photo_map.get(query.data, ("photo", "Photos"))

    res = pop_pending(user_id, kind="photo")
    if not res:
        await query.edit_message_text(msg.SESSION_EXPIRED)
        return
    links, source = res

    await record_user(user_id, user.username, user.first_name or "")

    # Always enqueue directly to send to Telegram chat
    for idx, url in enumerate(links, start=1):
        item_label = f"Link {idx}/{len(links)}" if len(links) > 1 else label
        job = DownloadJob(
            user_id=user_id,
            chat_id=chat_id,
            url=url,
            quality=format_choice,
            label=item_label,
            callback=process_job,
            save_locally=False,
        )
        await download_queue.add_job(job)

    await query.edit_message_text(
        msg.queued_photo(len(links), format_choice),
        parse_mode="Markdown",
    )


async def handle_folder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy folder callback fallback (if user clicked old button)."""
    query = update.callback_query
    await query.answer()

    from src.bot import download_queue, process_job

    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    lang = await get_lang(user_id)
    msg = Msg(lang)

    result = pop_pending_save(user_id)
    if not result:
        await query.edit_message_text(msg.SESSION_EXPIRED)
        return

    links, quality = result
    total = len(links)

    for idx, url in enumerate(links, start=1):
        label = f"Link {idx}/{total}"
        job = DownloadJob(
            user_id=user_id,
            chat_id=chat_id,
            url=url,
            quality=quality,
            label=label,
            callback=process_job,
            save_locally=False,
            save_dir=None,
        )
        await download_queue.add_job(job)

    await query.edit_message_text(
        msg.queued(total, quality, total),
        parse_mode="Markdown",
    )
