import unittest
from core.models import (
    ContentType,
    DownloadRequest,
    AudioMetadata,
    MediaResult,
    BypassStrategyInfo,
)


class TestCoreModels(unittest.TestCase):
    def test_content_type_enum(self):
        self.assertEqual(ContentType.VIDEO.value, "video")
        self.assertEqual(ContentType.PHOTO.value, "photo")
        self.assertEqual(ContentType.AUDIO.value, "audio")

    def test_download_request(self):
        req = DownloadRequest(url="https://vt.tiktok.com/ZSgPJ8EUB/", quality="1080p", user_id=123, chat_id=456)
        self.assertEqual(req.url, "https://vt.tiktok.com/ZSgPJ8EUB/")
        self.assertEqual(req.quality, "1080p")
        self.assertEqual(req.user_id, 123)
        self.assertEqual(req.chat_id, 456)
        self.assertEqual(req.label, "")

    def test_audio_metadata(self):
        meta = AudioMetadata(
            path="/tmp/audio.mp3",
            title="Cool Track",
            performer="Awesome Artist",
            duration=35,
            thumbnail_path="/tmp/thumb.jpg",
        )
        self.assertEqual(meta.path, "/tmp/audio.mp3")
        self.assertEqual(meta.title, "Cool Track")
        self.assertEqual(meta.performer, "Awesome Artist")
        self.assertEqual(meta.duration, 35)
        self.assertEqual(meta.thumbnail_path, "/tmp/thumb.jpg")

    def test_media_result(self):
        res = MediaResult(files=["/tmp/1.jpg", "/tmp/2.jpg"], content_type="photo", title="My Album")
        self.assertEqual(len(res.files), 2)
        self.assertEqual(res.content_type, "photo")
        self.assertEqual(res.title, "My Album")

    def test_bypass_strategy_info(self):
        info = BypassStrategyInfo(
            id="ssstik",
            name="SSSTik Cloud",
            description="Bypasses age gates",
            target="Age-restricted posts",
            is_active=True,
        )
        self.assertEqual(info.id, "ssstik")
        self.assertTrue(info.is_active)


if __name__ == "__main__":
    unittest.main()
