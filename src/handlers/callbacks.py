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
    _quality_map = {"quality_1080p": "1080p", "quality_1440p": "1440p", "quality_audio": "audio"}
    quality = _quality_map.get(query.data, "1080p")

    links = pop_pending(user_id)
    if not links:
        await query.edit_message_text(msg.SESSION_EXPIRED)
        return

    await record_user(user_id, user.username, user.first_name or "")

    # Batch (>1 link) → ask where to save; single link → send to chat as usual
    if len(links) > 1:
        store_pending_save(user_id, links, quality)
        await query.edit_message_text(
            msg.choose_folder(len(links)),
            parse_mode="Markdown",
            reply_markup=folder_keyboard(),
        )
        return

    # Single link — existing chat-send flow
    default_label = "Audio" if quality == "audio" else "Video"
    job = DownloadJob(
        user_id=user_id,
        chat_id=chat_id,
        url=links[0],
        quality=quality,
        label=default_label,
        callback=process_job,
    )
    position = await download_queue.add_job(job)
    await query.edit_message_text(
        msg.queued(1, quality, position),
        parse_mode="Markdown",
    )


async def handle_folder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User chose a save folder for the batch download."""
    query = update.callback_query
    await query.answer()

    from src.bot import download_queue, process_job

    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    lang = await get_lang(user_id)
    msg = Msg(lang)

    # callback_data = "folder_<path>"
    save_dir = query.data[len("folder_"):]

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
            save_locally=True,
            save_dir=save_dir,
        )
        await download_queue.add_job(job)

    await query.edit_message_text(
        msg.queued(total, quality, total),
        parse_mode="Markdown",
    )
