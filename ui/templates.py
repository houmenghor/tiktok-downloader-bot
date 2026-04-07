"""All user-facing message strings in one place for easy translation/editing."""


class Msg:
    # ── Commands ────────────────────────────────────────────────────────────
    START = (
        "👋 *TikTok Downloader Bot*\n\n"
        "Send me a TikTok link *or* upload a *.txt* file with one link per line.\n"
        "I'll ask you for the quality, then download and send everything back.\n\n"
        "Commands:\n"
        "/start — show this message\n"
        "/queue — show how many jobs are waiting"
    )

    @staticmethod
    def queue_size(size: int) -> str:
        return f"📋 Jobs currently in queue: *{size}*"

    # ── Link detection ───────────────────────────────────────────────────────
    NO_LINKS_FOUND = "⚠️ No TikTok links found. Please send a valid TikTok URL."
    NOT_A_TXT_FILE = "⚠️ Please upload a plain *.txt* file."
    FILE_TOO_LARGE = "⚠️ File is too large. Max 5 MB for a link list."
    NO_LINKS_IN_FILE = "⚠️ No TikTok links found in the uploaded file."

    @staticmethod
    def links_found(count: int, source: str = "message") -> str:
        noun = "link" if count == 1 else "links"
        icon = "📄" if source == "file" else "🔗"
        return f"{icon} Found *{count}* {noun}. Choose download quality:"

    # ── Queue feedback ───────────────────────────────────────────────────────
    SESSION_EXPIRED = "⚠️ Session expired. Please send the link(s) again."

    @staticmethod
    def queued(count: int, quality: str, position: int) -> str:
        noun = "link" if count == 1 else "links"
        return (
            f"✅ *{count}* {noun} added to queue at *{quality}*.\n"
            f"Queue size: *{position}* job(s). I'll send videos as they finish."
        )

    # ── Download progress ────────────────────────────────────────────────────
    @staticmethod
    def downloading(label: str, quality: str) -> str:
        return f"⏬ Downloading {label} ({quality})..."

    @staticmethod
    def sending_parts(label: str, total_parts: int) -> str:
        return f"📦 {label} is large — sending in {total_parts} parts."

    @staticmethod
    def video_caption(label: str, quality: str) -> str:
        return f"✅ {label} ({quality})"

    @staticmethod
    def part_caption(label: str, part: int, total: int, quality: str) -> str:
        return f"✅ {label} — Part {part}/{total} ({quality})"

    @staticmethod
    def download_failed(label: str, error: str) -> str:
        return f"❌ Failed to download {label}.\nError: {error}"
