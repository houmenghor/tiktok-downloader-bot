from telegram import Update
from telegram.ext import ContextTypes

from ui.templates import Msg


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(Msg.START, parse_mode="Markdown")


async def cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from src.bot import download_queue  # late import to avoid circular
    size = download_queue.qsize()
    await update.message.reply_text(Msg.queue_size(size), parse_mode="Markdown")
