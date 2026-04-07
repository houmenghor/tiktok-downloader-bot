from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def quality_keyboard() -> InlineKeyboardMarkup:
    """Return the quality-selection inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 1080p", callback_data="quality_1080p"),
            InlineKeyboardButton("🎥 1440p", callback_data="quality_1440p"),
        ]
    ])
