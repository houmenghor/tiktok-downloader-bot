import asyncio
import glob
import logging
import os
import re

from config.settings import settings
from core.models import AudioMetadata
from helper.file_utils import assert_file_exists
from helper.link_parser import is_photo_url
from services.bypass.manager import bypass_download_photos, bypass_download_audio
from services.bypass.native_web import resolve_redirect
from services.downloader.ytdlp_engine import sync_download_video, sync_download_audio
from services.media.video_splitter import split_video

logger = logging.getLogger(__name__)
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def collect_photo_files(output_dir: str, video_id: str) -> list[str]:
    """Find all image files downloaded for a photo post."""
    photos = []
    for ext in _IMAGE_EXTS:
        photos += glob.glob(os.path.join(output_dir, f"{video_id}*{ext}"))
    return sorted(photos)


def sync_probe(url: str) -> str:
    """Resolve URL redirects then check the final URL. Returns 'photo' or 'video'."""
    final_url = resolve_redirect(url)
    if is_photo_url(final_url):
        return "photo"
    return "video"


async def probe_url(url: str) -> str:
    """Async wrapper for sync_probe. Returns 'photo' or 'video'."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_probe, url)


async def download_audio(url: str, output_dir: str) -> AudioMetadata:
    """Download audio only with rich metadata and automatic bypass fallback."""
    loop = asyncio.get_event_loop()
    resolved_url = await loop.run_in_executor(None, resolve_redirect, url)

    clean_resolved = resolved_url.split("?")[0]
    ytdlp_audio_url = re.sub(r"/photo/", "/video/", clean_resolved) if is_photo_url(resolved_url) else url

    if is_photo_url(resolved_url):
        try:
            return await loop.run_in_executor(None, bypass_download_audio, resolved_url, output_dir)
        except Exception as exc:
            logger.info("Bypass audio failed for photo post (%s) — trying yt-dlp", exc)
            return await loop.run_in_executor(None, sync_download_audio, ytdlp_audio_url, output_dir)

    try:
        return await loop.run_in_executor(None, sync_download_audio, ytdlp_audio_url, output_dir)
    except Exception as exc:
        logger.info("yt-dlp failed to download audio (%s) — falling back to bypass cascade", exc)
        return await loop.run_in_executor(None, bypass_download_audio, resolved_url, output_dir)


async def download_video(url: str, quality: str, output_dir: str) -> tuple[list[str], str]:
    """Download video or photo slideshow with automatic multi-tier bypass cascade."""
    loop = asyncio.get_event_loop()
    resolved_url = await loop.run_in_executor(None, resolve_redirect, url)

    # If photo requested or URL is a photo/slideshow, run bypass photo cascade
    if quality in ("photo", "photo_both") or is_photo_url(resolved_url):
        photos, kind = await loop.run_in_executor(None, bypass_download_photos, resolved_url, output_dir)
        if photos:
            return photos, kind

    # Standard video download
    try:
        filepath, info = await loop.run_in_executor(None, sync_download_video, url, quality, output_dir)
        if os.path.splitext(filepath)[1].lower() in {".mp3", ".m4a", ".wav", ".aac", ".weba"}:
            raise RuntimeError("yt-dlp returned audio instead of video (photo post or restriction)")
    except Exception as exc:
        logger.info("yt-dlp video failed (%s) — running photo bypass cascade", exc)
        photos, kind = await loop.run_in_executor(None, bypass_download_photos, resolved_url, output_dir)
        if photos:
            return photos, kind
        raise RuntimeError("The post is unavailable. It may have been deleted, set to private, or region-locked by the creator.")

    ext = os.path.splitext(filepath)[1].lower()
    if ext in _IMAGE_EXTS or not os.path.exists(filepath):
        video_id = info.get("id", "")
        photos = collect_photo_files(output_dir, video_id)
        if photos:
            return photos, "photo"

    assert_file_exists(filepath)

    file_size = os.path.getsize(filepath)
    if file_size > settings.max_file_size_bytes:
        logger.info("File %.1f MB exceeds limit — splitting: %s", file_size / 1024 / 1024, filepath)
        parts = await split_video(filepath, settings.max_file_size_bytes)
        try:
            os.remove(filepath)
        except OSError:
            pass
        return parts, "video"

    return [filepath], "video"
