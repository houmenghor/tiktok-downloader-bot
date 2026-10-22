import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.handlers.commands import cmd_start, cmd_help, cmd_status, cmd_stats, cmd_bypass
from src.handlers.language import cmd_language, handle_language_callback


class TestCommandsIntegration(unittest.TestCase):
    def setUp(self):
        self.update = MagicMock()
        self.update.effective_user.id = 123456
        self.update.effective_user.username = "test_user"
        self.update.effective_user.first_name = "Menghor"
        self.update.message.reply_chat_action = AsyncMock()
        self.update.message.reply_text = AsyncMock()
        self.context = MagicMock()

    def test_cmd_start(self):
        async def _test():
            with patch("src.handlers.commands.get_lang", new_callable=AsyncMock, return_value="en"):
                await cmd_start(self.update, self.context)
                self.update.message.reply_text.assert_called_once()
                reply = self.update.message.reply_text.call_args[0][0]
                self.assertIn("TikTok Downloader Bot", reply)
                self.assertIn("/bypass", reply)

        asyncio.run(_test())

    def test_cmd_help(self):
        async def _test():
            with patch("src.handlers.commands.get_lang", new_callable=AsyncMock, return_value="en"):
                await cmd_help(self.update, self.context)
                self.update.message.reply_text.assert_called_once()
                reply = self.update.message.reply_text.call_args[0][0]
                self.assertIn("How to use", reply)
                self.assertIn("/bypass", reply)

        asyncio.run(_test())

    def test_cmd_status(self):
        async def _test():
            with patch("src.handlers.commands.get_lang", new_callable=AsyncMock, return_value="en"), \
                 patch("src.bot.download_queue.qsize", return_value=0):
                await cmd_status(self.update, self.context)
                self.update.message.reply_text.assert_called_once()
                reply = self.update.message.reply_text.call_args[0][0]
                self.assertIn("No waiting line", reply)

        asyncio.run(_test())

    def test_cmd_stats_includes_bypass_count(self):
        async def _test():
            mock_stats = {"total_users": 42, "total_downloads": 108}
            with patch("src.handlers.commands.get_lang", new_callable=AsyncMock, return_value="en"), \
                 patch("src.handlers.commands.get_stats", new_callable=AsyncMock, return_value=mock_stats):
                await cmd_stats(self.update, self.context)
                self.update.message.reply_text.assert_called_once()
                reply = self.update.message.reply_text.call_args[0][0]
                self.assertIn("42", reply)
                self.assertIn("108", reply)
                self.assertIn("Bypass Strategies: *4 Active*", reply)
                self.assertIn("/bypass", reply)

        asyncio.run(_test())

    def test_cmd_bypass_details(self):
        async def _test():
            with patch("src.handlers.commands.get_lang", new_callable=AsyncMock, return_value="en"):
                await cmd_bypass(self.update, self.context)
                self.update.message.reply_text.assert_called_once()
                reply = self.update.message.reply_text.call_args[0][0]
                self.assertIn("Active Bypass Strategies (4)", reply)
                self.assertIn("SSSTik Cloud Bypass", reply)
                self.assertIn("TikWM Multi-Host API", reply)
                self.assertIn("TikTok Native Web Extractor", reply)
                self.assertIn("Gallery-dl Engine", reply)

        asyncio.run(_test())

    def test_cmd_language_keyboard(self):
        async def _test():
            with patch("src.handlers.language.get_lang", new_callable=AsyncMock, return_value="en"):
                await cmd_language(self.update, self.context)
                self.update.message.reply_text.assert_called_once()
                markup = self.update.message.reply_text.call_args[1].get("reply_markup")
                self.assertIsNotNone(markup)
                btn_data = [btn.callback_data for row in markup.inline_keyboard for btn in row]
                self.assertIn("lang_en", btn_data)
                self.assertIn("lang_kh", btn_data)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
