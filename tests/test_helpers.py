import asyncio
import os
import shutil
import unittest

from helper.link_parser import extract_links, is_photo_url
from services.media.binary_resolver import get_ffmpeg_cmd, get_ffprobe_cmd, resolve_binary
from helper.user_store import get_lang, set_lang, record_user, get_stats


class TestHelpers(unittest.TestCase):
    def test_extract_single_and_multiple_links(self):
        text = """
        Check this out! https://vt.tiktok.com/ZSgP13XRP/
        and this photo: https://www.tiktok.com/@user/photo/1234567890123456789
        and another video: https://vt.tiktok.com/ZSgP1puU6/?k=1
        """
        links = extract_links(text)
        self.assertEqual(len(links), 3)
        self.assertIn("https://vt.tiktok.com/ZSgP13XRP/", links)
        self.assertIn("https://www.tiktok.com/@user/photo/1234567890123456789", links)
        self.assertIn("https://vt.tiktok.com/ZSgP1puU6/?k=1", links)

    def test_is_photo_url(self):
        photo_url = "https://www.tiktok.com/@theary2405/photo/7698650624249875720"
        video_url = "https://www.tiktok.com/@theary2405/video/7698650624249875720"
        self.assertTrue(is_photo_url(photo_url))
        self.assertFalse(is_photo_url(video_url))

    def test_binary_resolver_cross_platform(self):
        # Even if a Windows .exe path is passed, on Linux it resolves to system binary
        resolved_ffmpeg = resolve_binary("assets/ffmpeg.exe", "ffmpeg")
        resolved_ffprobe = resolve_binary("assets/ffprobe.exe", "ffprobe")

        self.assertTrue(shutil.which(resolved_ffmpeg) is not None or resolved_ffmpeg == "ffmpeg")
        self.assertTrue(shutil.which(resolved_ffprobe) is not None or resolved_ffprobe == "ffprobe")
        self.assertFalse(resolved_ffmpeg.endswith(".exe"))
        self.assertFalse(resolved_ffprobe.endswith(".exe"))

    def test_user_store_operations(self):
        async def _test():
            test_uid = 9999991
            await record_user(test_uid, "tester", "QA Test")
            await set_lang(test_uid, "kh")
            lang = await get_lang(test_uid)
            self.assertEqual(lang, "kh")

            await set_lang(test_uid, "en")
            lang_en = await get_lang(test_uid)
            self.assertEqual(lang_en, "en")

            stats = await get_stats()
            self.assertGreaterEqual(stats["total_users"], 1)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
