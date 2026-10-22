from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def quality_keyboard() -> InlineKeyboardMarkup:
    """Return the quality-selection inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1080p (HD)", callback_data="quality_1080p"),
            InlineKeyboardButton("1440p (HD)", callback_data="quality_1440p"),
            InlineKeyboardButton("2160p (4K)", callback_data="quality_2160p"),
        ],
        [
            InlineKeyboardButton("🎵 Audio only", callback_data="quality_audio"),
        ],
    ])


def photo_keyboard() -> InlineKeyboardMarkup:
    """Return format-selection keyboard for TikTok photo slideshows."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🖼 Photos only", callback_data="photo_photos"),
            InlineKeyboardButton("🎵 Audio only", callback_data="photo_audio"),
        ],
        [
            InlineKeyboardButton("📦 Photos + Audio", callback_data="photo_both"),
        ],
    ])


def language_keyboard() -> InlineKeyboardMarkup:
    """Return the language-selection inline keyboard."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton("🇰🇭 ខ្មែរ", callback_data="lang_kh"),
    ]])


def folder_keyboard() -> InlineKeyboardMarkup:
    """Save options for batch .txt file downloads."""
    home = Path.home()
    buttons = [
        [InlineKeyboardButton("💬 Send all to Telegram Chat", callback_data="folder_chat")],
        [InlineKeyboardButton(f"📁 {home / 'Downloads' / 'Telegram Desktop'}", callback_data=f"folder_{home / 'Downloads' / 'Telegram Desktop'}")],
        [InlineKeyboardButton(f"💾 {home / 'Downloads'}", callback_data=f"folder_{home / 'Downloads'}")],
        [InlineKeyboardButton(f"🖥 {home / 'Desktop'}", callback_data=f"folder_{home / 'Desktop'}")],
    ]
    return InlineKeyboardMarkup(buttons)
