import os
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


def get_user_download_dir(user_id: int) -> str:
    """Return (and create) a per-user subdirectory inside DOWNLOAD_DIR."""
    path = os.path.join(settings.download_dir, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_files(paths: list[str]) -> None:
    """Delete a list of file paths silently. Used after sending videos."""
    for path in paths:
        try:
            os.remove(path)
            logger.debug("Deleted: %s", path)
        except OSError as exc:
            logger.warning("Could not delete %s: %s", path, exc)


def resolve_mp4_path(raw_path: str) -> str:
    """yt-dlp sometimes writes '<id>.webm' before merging to '<id>.mp4'.
    Return the .mp4 path if it exists, otherwise return raw_path as-is.
    """
    base, _ = os.path.splitext(raw_path)
    mp4 = base + ".mp4"
    return mp4 if os.path.exists(mp4) else raw_path


def assert_file_exists(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Expected file not found after download: {path}")
