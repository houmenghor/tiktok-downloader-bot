from telegram import Update
from telegram import ChatAction
from telegram.ext import ContextTypes

from config.settings import settings
from helper.user_store import get_stats, get_lang
from ui.templates import Msg


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await get_lang(update.effective_user.id)
    msg = Msg(lang)
    if settings.maintenance:
        await update.message.reply_text(msg.MAINTENANCE, parse_mode="Markdown")
        return
    await update.message.reply_chat_action(ChatAction.TYPING)
    await update.message.reply_text(msg.START, parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from src.bot import download_queue  # late import to avoid circular
    lang = await get_lang(update.effective_user.id)
    if settings.maintenance:
        await update.message.reply_text(Msg(lang).MAINTENANCE, parse_mode="Markdown")
        return
    await update.message.reply_chat_action(ChatAction.TYPING)
    size = download_queue.qsize()
    await update.message.reply_text(Msg(lang).queue_size(size), parse_mode="Markdown")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await get_lang(update.effective_user.id)
    if settings.maintenance:
        await update.message.reply_text(Msg(lang).MAINTENANCE, parse_mode="Markdown")
        return
    await update.message.reply_chat_action(ChatAction.TYPING)
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
