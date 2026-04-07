import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "/tmp/tiktok_downloads")
MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "3"))
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "45"))  # chunk size in MB
COOKIES_FILE: str | None = os.getenv("COOKIES_FILE")  # optional: path to cookies.txt for TikTok

MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
