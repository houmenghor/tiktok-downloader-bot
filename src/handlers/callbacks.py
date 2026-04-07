import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.messages import pop_pending
from src.queue_manager import DownloadJob
from ui.templates import Msg

logger = logging.getLogger(__name__)


async def handle_quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User pressed a quality button → enqueue all their pending links."""
    query = update.callback_query
    await query.answer()

    from src.bot import download_queue, process_job  # late import — avoids circular dep

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    _quality_map = {"quality_1080p": "1080p", "quality_1440p": "1440p"}
    quality = _quality_map.get(query.data, "1080p")

    links = pop_pending(user_id)
    if not links:
        await query.edit_message_text(Msg.SESSION_EXPIRED)
        return

    total = len(links)
    position = 0
    for idx, url in enumerate(links, start=1):
        label = f"Link {idx}/{total}" if total > 1 else "Video"
        job = DownloadJob(
            user_id=user_id,
            chat_id=chat_id,
            url=url,
            quality=quality,
            label=label,
            callback=process_job,
        )
        position = await download_queue.add_job(job)

    await query.edit_message_text(
        Msg.queued(total, quality, position),
        parse_mode="Markdown",
    )
