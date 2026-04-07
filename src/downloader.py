import asyncio
import logging
import os

import yt_dlp

from config.settings import settings
from helper.file_utils import resolve_mp4_path, assert_file_exists
from helper.splitter import split_video

logger = logging.getLogger(__name__)


_HEIGHT_MAP = {"1080p": "1080", "1440p": "1440"}


def _build_ydl_opts(quality: str, output_dir: str) -> dict:
    height = _HEIGHT_MAP.get(quality, "1080")
    fmt = (
        f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]"
        f"/bestvideo[height<={height}]+bestaudio"
        f"/best[height<={height}][ext=mp4]"
        f"/best[ext=mp4]/best"
    )
    opts: dict = {
        "format": fmt,
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": 30,
        # Use local ffmpeg/ffprobe if configured
        "ffmpeg_location": os.path.dirname(settings.ffmpeg_path) or None,
    }
    if settings.cookies_file and os.path.isfile(settings.cookies_file):
        opts["cookiefile"] = settings.cookies_file
    return opts


def _sync_download(url: str, quality: str, output_dir: str) -> str:
    """Blocking download — run inside executor to avoid blocking the event loop."""
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = _build_ydl_opts(quality, output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        raw_path = ydl.prepare_filename(info)
    return resolve_mp4_path(raw_path)


async def download_video(url: str, quality: str, output_dir: str) -> list[str]:
    """Download a TikTok video and return a list of file paths to send.

    If the file is within the size limit → returns [filepath].
    If the file exceeds the limit → splits with FFmpeg → returns [part1, part2, …].
    """
    loop = asyncio.get_event_loop()
    filepath = await loop.run_in_executor(None, _sync_download, url, quality, output_dir)
    assert_file_exists(filepath)

    file_size = os.path.getsize(filepath)
    if file_size > settings.max_file_size_bytes:
        logger.info(
            "File %.1f MB exceeds limit — splitting: %s",
            file_size / 1024 / 1024,
            filepath,
        )
        parts = await split_video(filepath, settings.max_file_size_bytes)
        try:
            os.remove(filepath)
        except OSError:
            pass
        return parts

    return [filepath]
