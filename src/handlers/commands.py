from telegram import Update
from telegram.ext import ContextTypes

from helper.user_store import get_stats, get_lang
from ui.templates import Msg


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await get_lang(update.effective_user.id)
    await update.message.reply_text(Msg(lang).START, parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from src.bot import download_queue  # late import to avoid circular
    lang = await get_lang(update.effective_user.id)
    size = download_queue.qsize()
    await update.message.reply_text(Msg(lang).queue_size(size), parse_mode="Markdown")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await get_lang(update.effective_user.id)
    stats = await get_stats()
    if lang == "kh":
        text = (
            f"📊 *ស្ថិតិ Bot*\n\n"
            f"👤 ចំនួនអ្នកប្រើ: *{stats['total_users']}*\n"
            f"⬇️ ចំនួន download សរុប: *{stats['total_downloads']}*"
        )
    else:
        text = (
            f"📊 *Bot Stats*\n\n"
            f"👤 Total users: *{stats['total_users']}*\n"
            f"⬇️ Total downloads: *{stats['total_downloads']}*"
        )
    await update.message.reply_text(text, parse_mode="Markdown")
