from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def quality_keyboard() -> InlineKeyboardMarkup:
    """Return the quality-selection inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 1080p", callback_data="quality_1080p"),
            InlineKeyboardButton("🎥 1440p", callback_data="quality_1440p"),
        ],
        [
            InlineKeyboardButton("🎵 Audio only", callback_data="quality_audio"),
        ],
    ])


def language_keyboard() -> InlineKeyboardMarkup:
    """Return the language-selection inline keyboard."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton("🇰🇭 ខ្មែរ", callback_data="lang_kh"),
    ]])


def folder_keyboard() -> InlineKeyboardMarkup:
    """Preset save-folder options for batch downloads — shows real resolved paths."""
    home = Path.home()
    folders = [
        ("📱 " + str(home / "Downloads" / "Telegram Desktop"), str(home / "Downloads" / "Telegram Desktop")),
        ("💾 " + str(home / "Downloads"),                      str(home / "Downloads")),
        ("🖥 " + str(home / "Desktop"),                        str(home / "Desktop")),
    ]
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"folder_{path}")]
        for label, path in folders
    ]
    return InlineKeyboardMarkup(buttons)
