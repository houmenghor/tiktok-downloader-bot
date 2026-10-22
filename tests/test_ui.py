import unittest
from ui.keyboards import quality_keyboard, photo_keyboard, language_keyboard
from ui.templates import Msg
from core.models import BypassStrategyInfo


class TestUIAndKeyboards(unittest.TestCase):
    def test_quality_keyboard_structure(self):
        kb = quality_keyboard()
        button_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        self.assertIn("quality_1080p", button_data)
        self.assertIn("quality_1440p", button_data)
        self.assertIn("quality_2160p", button_data)
        self.assertIn("quality_audio", button_data)

    def test_photo_keyboard_structure(self):
        kb = photo_keyboard()
        button_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        self.assertIn("photo_photos", button_data)
        self.assertIn("photo_audio", button_data)
        self.assertIn("photo_both", button_data)

    def test_language_keyboard_structure(self):
        kb = language_keyboard()
        button_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        self.assertIn("lang_en", button_data)
        self.assertIn("lang_kh", button_data)

    def test_templates_bilingual_switch(self):
        msg_en = Msg("en")
        msg_kh = Msg("kh")

        self.assertIn("How to use", msg_en.HELP)
        self.assertIn("របៀបប្រើ", msg_kh.HELP)

        self.assertIn("Found *3* links", msg_en.links_found(3))
        self.assertIn("រកឃើញ *3* link", msg_kh.links_found(3))

        self.assertIn("Downloading at *1080p*", msg_en.queued(1, "1080p", 1))
        self.assertIn("កំពុង download *1080p*", msg_kh.queued(1, "1080p", 1))

    def test_templates_bypass_info(self):
        msg = Msg("en")
        mock_strategies = [
            BypassStrategyInfo(
                id="native_web",
                name="Native Web Extractor",
                description="Extracts imagePost",
                target="Normal Slideshows",
                is_active=True,
            ),
            BypassStrategyInfo(
                id="ssstik",
                name="SSSTik Bypass",
                description="Bypasses age restrictions",
                target="Sensitive Posts",
                is_active=True,
            ),
        ]
        text = msg.bypass_info(mock_strategies)
        self.assertIn("Active Bypass Strategies (2)", text)
        self.assertIn("Native Web Extractor", text)
        self.assertIn("SSSTik Bypass", text)
        self.assertIn("Sensitive Posts", text)


if __name__ == "__main__":
    unittest.main()
