import logging

from telegram import Update
from telegram.ext import ContextTypes

from helper.user_store import get_lang, set_lang
from ui.keyboards import language_keyboard
from ui.templates import Msg

logger = logging.getLogger(__name__)


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show language selection keyboard."""
    user_id = update.effective_user.id
    lang = await get_lang(user_id)
    msg = Msg(lang)
    await update.message.reply_text(msg.CHOOSE_LANGUAGE, reply_markup=language_keyboard())


async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User pressed a language button — save preference and confirm."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = "en" if query.data == "lang_en" else "kh"
    await set_lang(user_id, lang)

    msg = Msg(lang)
    await query.edit_message_text(msg.language_set(lang))
