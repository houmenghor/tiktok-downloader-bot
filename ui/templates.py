"""All user-facing message strings — English (en) and Khmer (kh).

Usage:
    msg = Msg(lang)          # lang is "en" or "kh"
    msg.START                # property -> str
    msg.downloading(label, quality)  # method -> str
"""
from __future__ import annotations


class Msg:
    def __init__(self, lang: str = "en") -> None:
        self._kh = lang == "kh"

    def _p(self, en: str, kh: str) -> str:
        return kh if self._kh else en

    # Commands
    @property
    def START(self) -> str:
        return self._p(
            "👋 *TikTok Downloader Bot*\n\n"
            "Send me a TikTok link *or* upload a *.txt* file with one link per line.\n"
            "I'll ask you for the quality, then download and send everything back.\n\n"
            "Commands:\n"
            "/start — show this message\n"
            "/status — show how many downloads are in progress\n"
            "/stats — show total users and downloads\n"
            "/language — change language\n\n"
         "👨‍💻 *Developer:* Hou Menghor\n"
         "📬 [t.me/houmenghor](https://t.me/houmenghor)",

            "👋 *TikTok Downloader Bot*\n\n"
            "ផ្ញើ TikTok link ឬ upload file *.txt* ដែលមាន link មួយក្នុងមួយបន្ទាត់។\n"
            "ខ្ញុំនឹងសួររកគុណភាព រួចហើយ download និង send វិញ។\n\n"
            "ពាក្យបញ្ជា:\n"
            "/start — បង្ហាញសារនេះ\n"
            "/status — បង្ហាញចំនួន download កំពុងដំណើរការ\n"
            "/stats — បង្ហាញចំនួនអ្នកប្រើ និង download\n"
            "/language — ប្ដូរភាសា\n\n"
         "👨‍💻 *អ្នកបង្កើត:* ហ៊ួរ ម៉េងហ័រ\n"
         "📬 [t.me/houmenghor](https://t.me/houmenghor)",
        )

    @property
    def HELP(self) -> str:
        return self._p(
            "📖 *How to use TikTok Downloader KH*\n\n"
            "*Download a video:*\n"
            "1\. Send a TikTok video link\n"
            "2\. Choose quality: 1080p, 1440p, 2160p, or Audio\n"
            "3\. Receive your file instantly\n\n"
            "*Download photos/slideshow:*\n"
            "Just send a TikTok photo link — no quality selection needed\n\n"
            "*Batch download (multiple links):*\n"
            "Send a \.txt file with one TikTok link per line\n\n"
            "*Commands:*\n"
            "/start — Welcome message\n"
            "/help — Show this help\n"
            "/status — Queue status\n"
            "/stats — Total users & downloads\n"
            "/language — Change language\n\n"
            "👨\u200d💻 *Developer:* Hou Menghor\n"
            "📬 [t\.me/houmenghor](https://t.me/houmenghor)",

            "📖 *របៀបប្រើ TikTok Downloader KH*\n\n"
            "*ដោនឡូតវីដេអូ:*\n"
            "1\. ផ្ញើ link TikTok\n"
            "2\. ជ្រើសគុណភាព: 1080p, 1440p, 2160p, ឬ Audio\n"
            "3\. ទទួលឯកសារភ្លាមៗ\n\n"
            "*ដោនឡូតរូបភាព/slideshow:*\n"
            "ផ្ញើ TikTok photo link\n\n"
            "*ដោនឡូតច្រើន link:*\n"
            "ផ្ញើ file \.txt ដែលមាន link មួយក្នុងមួយបន្ទាត់\n\n"
            "*ពាក្យបញ្ជា:*\n"
            "/start — សារស្វាគមន៍\n"
            "/help — បង្ហាញជំនួយ\n"
            "/status — ស្ថានភាព queue\n"
            "/stats — ចំនួនអ្នកប្រើ & download\n"
            "/language — ប្ដូរភាសា\n\n"
            "👨\u200d💻 *អ្នកបង្កើត:* ហ៊ួរ ម៉េងហ័រ\n"
            "📬 [t\.me/houmenghor](https://t.me/houmenghor)",
        )

    @property
    def MAINTENANCE(self) -> str:
        return self._p(
            "🔧 *Bot is under maintenance.*\n\nPlease try again in a few minutes.",
            "🔧 *Bot កំពុងត្រូវបានថែទាំ។*\n\nសូមព្យាយាមម្ដងទៀតក្នុងពីរបីនាទី។",
        )

    def queue_size(self, size: int) -> str:
        return self._p(
            f"📋 Jobs currently in queue: *{size}*",
            f"📋 ចំនួន Job ក្នុង Queue: *{size}*",
        )

    # Link detection
    @property
    def NO_LINKS_FOUND(self) -> str:
        return self._p(
            "⚠️ No TikTok links found. Please send a valid TikTok URL.",
            "⚠️ រកមិនឃើញ TikTok link។ សូម send URL ត្រឹមត្រូវ។",
        )

    @property
    def NOT_A_TXT_FILE(self) -> str:
        return self._p(
            "⚠️ Please upload a plain *.txt* file.",
            "⚠️ សូម upload file *.txt* ។",
        )

    @property
    def FILE_TOO_LARGE(self) -> str:
        return self._p(
            "⚠️ File is too large. Max 5 MB for a link list.",
            "⚠️ File ធំពេក។ អតិបរមា 5 MB សម្រាប់ link list។",
        )

    @property
    def NO_LINKS_IN_FILE(self) -> str:
        return self._p(
            "⚠️ No TikTok links found in the uploaded file.",
            "⚠️ រកមិនឃើញ TikTok link ក្នុង file ដែល upload មក។",
        )

    def links_found(self, count: int, source: str = "message") -> str:
        noun = "link" if count == 1 else "links"
        icon = "📄" if source == "file" else "🔗"
        return self._p(
            f"{icon} Found *{count}* {noun}. Choose download quality:",
            f"{icon} រកឃើញ *{count}* link។ ជ្រើសគុណភាព download:",
        )

    # Queue feedback
    @property
    def SESSION_EXPIRED(self) -> str:
        return self._p(
            "⚠️ Session expired. Please send the link(s) again.",
            "⚠️ Session ផុតកំណត់។ សូម send link ម្ដងទៀត។",
        )

    def queued(self, count: int, quality: str, position: int) -> str:
        return self._p(
            f"✅ Got it! Downloading at *{quality}* — I'll send it when it's ready.",
            f"✅ បានទទួល! កំពុង download *{quality}* — ខ្ញុំនឹង send ពេលរួចរាល់។",
        )

    def queued_photo(self, count: int) -> str:
        noun = "slideshow" if count == 1 else "slideshows"
        return self._p(
            f"🖼 Got it! Downloading {count} photo {noun} — I'll send them when ready.",
            f"🖼 បានទទួល! កំពុង download {count} រូបភាព — ខ្ញុំនឹង send ពេលរួចរាល់។",
        )

    # Download progress
    def downloading_photo(self, label: str) -> str:
        return self._p(
            f"⏬ Downloading {label} (photos)...",
            f"⏬ កំពុង download {label} (រូបភាព)...",
        )

    def downloading(self, label: str, quality: str) -> str:
        return self._p(
            f"⏬ Downloading {label} ({quality})...",
            f"⏬ កំពុង download {label} ({quality})...",
        )

    def sending_parts(self, label: str, total_parts: int) -> str:
        return self._p(
            f"📦 {label} is large — sending in {total_parts} parts.",
            f"📦 {label} ធំ — កំពុង send ជា {total_parts} ផ្នែក។",
        )

    @property
    def SAVE_TIP(self) -> str:
        return self._p(
            "💡 Tip: If the video lags in Telegram, save it to your phone — it will play smoothly.",
            "💡 គន្លឹះ: បើវីដេអូទាក់ក្នុង Telegram សូម save មកទូរស័ព្ទ វានឹងរលូននៅក្នុង Gallery។",
        )

    def video_caption(self, label: str, quality: str) -> str:
        return f"✅ {label} ({quality})"

    def part_caption(self, label: str, part: int, total: int, quality: str) -> str:
        return self._p(
            f"✅ {label} — Part {part}/{total} ({quality})",
            f"✅ {label} — ផ្នែក {part}/{total} ({quality})",
        )

    def download_failed(self, label: str, error: str) -> str:
        return self._p(
            f"❌ Failed to download {label}.\nError: {error}",
            f"❌ Download {label} បរាជ័យ។\nកំហុស: {error}",
        )

    # Audio
    def downloading_audio(self, label: str) -> str:
        return self._p(
            f"⏬ Extracting audio for {label}...",
            f"⏬ កំពុងស្រង់ audio {label}...",
        )

    def audio_caption(self, label: str) -> str:
        return f"🎵 {label}"

    # Photo slideshow
    def sending_photos(self, label: str, count: int) -> str:
        noun = "photo" if count == 1 else "photos"
        return self._p(
            f"🖼 {label} — sending {count} {noun}.",
            f"🖼 {label} — កំពុង send {count} រូបភាព។",
        )

    def photo_caption(self, label: str, idx: int, total: int) -> str:
        if total == 1:
            return f"🖼 {label}"
        return f"🖼 {label} — {idx}/{total}"

    @property
    def BACK_ONLINE(self) -> str:
        return self._p(
            "✅ *Bot is back online!*\n\nSorry for the wait — everything is working normally now. Send me a TikTok link to get started! 🎉",
            "✅ *Bot បានត្រលប់មកវិញហើយ!*\n\nសូមអភ័យទោសចំពោះការរង់ចាំ — អ្វីៗដំណើរការធម្មតាហើយ។ ផ្ញើ TikTok link មកខ្ញុំបានហើយ! 🎉",
        )

    # Language
    @property
    def CHOOSE_LANGUAGE(self) -> str:
        return self._p("🌐 Choose your language:", "🌐 ជ្រើសរើសភាសា:")

    def language_set(self, lang: str) -> str:
        return self._p(
            "✅ Language set to English." if lang == "en" else "✅ Language set to Khmer (ខ្មែរ).",
            "✅ បានកំណត់ភាសាអង់គ្លេស។" if lang == "en" else "✅ បានកំណត់ភាសាខ្មែរ។",
        )

    # ── Batch save-to-folder ──────────────────────────────────────────────────
    def choose_folder(self, count: int) -> str:
        return self._p(
            f"📂 *{count} links* ready. Choose a folder to save the files:",
            f"📂 *{count} link* រួចរាល់។ ជ្រើសថតដើម្បីរក្សាទុកឯកសារ:",
        )

    def saved_file(self, label: str, folder: str) -> str:
        return self._p(
            f"✅ Saved: *{label}* → `{folder}`",
            f"✅ រក្សាទុករួច: *{label}* → `{folder}`",
        )

    def batch_done(self, count: int, folder: str) -> str:
        return self._p(
            f"📁 Done! *{count}* file(s) saved to:\n`{folder}`",
            f"📁 រួចរាល់! *{count}* ឯកសារ បានរក្សាទុកក្នុង:\n`{folder}`",
        )
