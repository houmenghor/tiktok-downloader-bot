import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers.messages import _store_pending, pop_pending
from src.handlers.callbacks import handle_quality_callback, handle_photo_callback
from src.queue_manager import DownloadJob


class TestHandlersIntegration(unittest.TestCase):
    def test_pending_storage_source_tagging(self):
        links = ["https://vt.tiktok.com/ZSgP13XRP/", "https://vt.tiktok.com/ZSgPJ8EUB/"]
        user_id = 888123

        # Message source
        _store_pending(user_id, links, kind="video", source="message")
        popped = pop_pending(user_id, kind="video")
        self.assertIsNotNone(popped)
        popped_links, source = popped
        self.assertEqual(len(popped_links), 2)
        self.assertEqual(source, "message")

        # File source
        _store_pending(user_id, links, kind="video", source="file")
        popped_file = pop_pending(user_id, kind="video")
        self.assertIsNotNone(popped_file)
        popped_links_f, source_f = popped_file
        self.assertEqual(source_f, "file")

    def test_quality_callback_multiple_links_direct_chat_delivery(self):
        async def _test():
            user_id = 777123
            chat_id = 777456
            links = ["https://vt.tiktok.com/ZSgP13XRP/", "https://vt.tiktok.com/ZSgP1puU6/"]
            _store_pending(user_id, links, kind="video", source="message")

            update = MagicMock()
            update.effective_user.id = user_id
            update.effective_user.username = "testuser"
            update.effective_user.first_name = "Tester"
            update.effective_chat.id = chat_id
            update.callback_query.data = "quality_2160p"
            update.callback_query.answer = AsyncMock()
            update.callback_query.edit_message_text = AsyncMock()

            context = MagicMock()

            with patch("src.handlers.callbacks.get_lang", new_callable=AsyncMock, return_value="en"), \
                 patch("src.handlers.callbacks.record_user", new_callable=AsyncMock), \
                 patch("src.bot.download_queue.add_job", new_callable=AsyncMock) as mock_add_job:
                await handle_quality_callback(update, context)

                # Verify 2 jobs were added
                self.assertEqual(mock_add_job.call_count, 2)
                for call_args in mock_add_job.call_args_list:
                    job: DownloadJob = call_args[0][0]
                    # CRITICAL: Must be save_locally=False so it uploads to Telegram chat!
                    self.assertFalse(job.save_locally)
                    self.assertEqual(job.chat_id, chat_id)
                    self.assertEqual(job.quality, "2160p")

                # Verify message edited with confirmation, NOT asking for folder!
                update.callback_query.edit_message_text.assert_called_once()
                msg_text = update.callback_query.edit_message_text.call_args[0][0]
                self.assertNotIn("folder", msg_text.lower())
                self.assertNotIn("desktop", msg_text.lower())

        asyncio.run(_test())

    def test_photo_callback_multiple_links_direct_chat_delivery(self):
        async def _test():
            user_id = 777124
            chat_id = 777457
            links = ["https://vt.tiktok.com/ZSgPJ8EUB/"]
            _store_pending(user_id, links, kind="photo", source="message")

            update = MagicMock()
            update.effective_user.id = user_id
            update.effective_user.username = "photouser"
            update.effective_user.first_name = "PhotoTester"
            update.effective_chat.id = chat_id
            update.callback_query.data = "photo_both"
            update.callback_query.answer = AsyncMock()
            update.callback_query.edit_message_text = AsyncMock()

            context = MagicMock()

            with patch("src.handlers.callbacks.get_lang", new_callable=AsyncMock, return_value="en"), \
                 patch("src.handlers.callbacks.record_user", new_callable=AsyncMock), \
                 patch("src.bot.download_queue.add_job", new_callable=AsyncMock) as mock_add_job:
                await handle_photo_callback(update, context)

                self.assertEqual(mock_add_job.call_count, 1)
                job: DownloadJob = mock_add_job.call_args[0][0]
                self.assertFalse(job.save_locally)
                self.assertEqual(job.quality, "photo_both")

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
