import asyncio
import os
import tempfile
import unittest

from services.downloader import download_video, download_audio, probe_url


class TestDownloadPipelineQA(unittest.TestCase):
    def test_probe_url_photo_detection(self):
        async def _test():
            kind = await probe_url("https://vt.tiktok.com/ZSgPJ8EUB/")
            self.assertEqual(kind, "photo")

        asyncio.run(_test())

    def test_sensitive_post_photo_and_audio_download(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmp:
                url = "https://vt.tiktok.com/ZSgPJ8EUB/"

                # Test 1: Photo extraction
                photos, kind = await download_video(url, "photo_both", tmp)
                self.assertEqual(kind, "photo")
                self.assertGreaterEqual(len(photos), 1)
                for p in photos:
                    self.assertTrue(os.path.exists(p))
                    self.assertGreater(os.path.getsize(p), 10_000, "Photo file should be > 10KB")

                # Test 2: Audio extraction with metadata
                meta = await download_audio(url, tmp)
                self.assertTrue(os.path.exists(meta.path))
                self.assertGreater(os.path.getsize(meta.path), 10_000, "Audio file should be > 10KB")
                self.assertTrue(len(meta.title) > 0, "Audio title should not be empty")
                self.assertTrue(len(meta.performer) > 0, "Audio performer should not be empty")
                self.assertGreater(meta.duration, 0, "Audio duration should be positive")
                if meta.thumbnail_path:
                    self.assertTrue(os.path.exists(meta.thumbnail_path))
                    self.assertGreater(os.path.getsize(meta.thumbnail_path), 1_000)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
