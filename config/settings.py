import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    download_dir: str = field(default_factory=lambda: os.getenv(
        "DOWNLOAD_DIR",
        str(Path.home() / "Downloads" / "Telegram Desktop"),
    ))
    max_workers: int = field(default_factory=lambda: int(os.getenv("MAX_WORKERS", "3")))
    max_file_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_MB", "45")))
    cookies_file: str | None = field(default_factory=lambda: os.getenv("COOKIES_FILE"))
    # TTL (seconds) for pending quality-selection sessions per user
    session_ttl: int = field(default_factory=lambda: int(os.getenv("SESSION_TTL", "300")))
    # Path to ffmpeg/ffprobe executables (leave empty to use system PATH)
    ffmpeg_path: str = field(default_factory=lambda: os.getenv("FFMPEG_PATH", "ffmpeg"))
    ffprobe_path: str = field(default_factory=lambda: os.getenv("FFPROBE_PATH", "ffprobe"))
    # Persistent user data file — mount this path as a Docker volume to survive rebuilds
    users_file: str = field(default_factory=lambda: os.getenv("USERS_FILE", "/data/users.json"))
    # MongoDB URI — if set, MongoDB is used instead of the JSON file (required on Render free)
    mongo_uri: str | None = field(default_factory=lambda: os.getenv("MONGO_URI"))

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    def validate(self) -> None:
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is not set. Add it to your .env file.")


# Singleton — import this everywhere
settings = Settings()
