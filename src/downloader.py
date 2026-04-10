import asyncio
import glob
import logging
import os
import shutil
import tempfile

import yt_dlp

from config.settings import settings
from helper.file_utils import resolve_mp4_path, assert_file_exists
from helper.link_parser import is_photo_url
from helper.splitter import split_video

logger = logging.getLogger(__name__)

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_HEIGHT_MAP = {"1080p": "1080", "1440p": "1440", "2160p": "2160"}


def _base_opts(output_dir: str) -> dict:
    """Common yt-dlp options shared by all download modes."""
    opts: dict = {
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": 30,
        "ffmpeg_location": os.path.dirname(settings.ffmpeg_path) or None,
    }
    if settings.cookies_file and os.path.isfile(settings.cookies_file):
        opts["cookiefile"] = settings.cookies_file
    return opts


def _build_ydl_opts(quality: str, output_dir: str) -> dict:
    height = _HEIGHT_MAP.get(quality, "1080")
    # Prefer h264 (avc) — universally supported by all phones without lag
    fmt = (
        f"bestvideo[height<={height}][ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]"
        f"/bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]"
        f"/bestvideo[height<={height}]+bestaudio"
        f"/best[height<={height}][ext=mp4]"
        f"/best[ext=mp4]/best"
    )
    opts = _base_opts(output_dir)
    opts["format"] = fmt
    opts["merge_output_format"] = "mp4"
    # Merger+ffmpeg_o applies args to the output file — required for faststart to work
    opts["postprocessor_args"] = {"Merger+ffmpeg_o": ["-movflags", "+faststart"]}
    return opts


def _build_audio_opts(output_dir: str) -> dict:
    opts = _base_opts(output_dir)
    opts["format"] = "bestaudio/best"
    opts["postprocessors"] = [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }]
    opts["outtmpl"] = os.path.join(output_dir, "%(id)s.%(ext)s")
    return opts


def _sync_download(url: str, quality: str, output_dir: str) -> tuple[str, dict]:
    """Blocking video/photo download. Returns (raw_path, info)."""
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = _build_ydl_opts(quality, output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        raw_path = ydl.prepare_filename(info)
    return resolve_mp4_path(raw_path), info


def _sync_download_audio(url: str, output_dir: str) -> str:
    """Blocking audio extraction. Returns path to .mp3 file."""
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = _build_audio_opts(output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # After postprocessor, file is .mp3
        base = os.path.join(output_dir, info["id"])
        mp3_path = base + ".mp3"
        if os.path.exists(mp3_path):
            return mp3_path
        # Fallback: find any mp3 in output_dir matching id
        matches = glob.glob(base + "*.mp3")
        if matches:
            return matches[0]
        raise FileNotFoundError(f"Audio file not found after download: {base}.mp3")


def _collect_photo_files(output_dir: str, video_id: str) -> list[str]:
    """Find all image files downloaded for a photo slideshow post."""
    photos = []
    for ext in _IMAGE_EXTS:
        photos += glob.glob(os.path.join(output_dir, f"{video_id}*{ext}"))
    return sorted(photos)


def _sync_download_photos_gdl(url: str, output_dir: str) -> list[str]:
    """Fallback photo downloader using gallery-dl Python API (handles TikTok image slideshows)."""
    import gallery_dl.job
    import gallery_dl.config
    os.makedirs(output_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        gallery_dl.config.set(("extractor",), "base-directory", tmp)
        gallery_dl.config.set(("extractor",), "filename", "{id}_{num}.{extension}")
        job = gallery_dl.job.DownloadJob(url)
        job.run()
        photos = []
        for root, _dirs, files in os.walk(tmp):
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext in _IMAGE_EXTS:  # skip .mp3 and other non-image files
                    src = os.path.join(root, fname)
                    dst = os.path.join(output_dir, fname)
                    shutil.move(src, dst)
                    photos.append(dst)
    return sorted(photos)


async def download_audio(url: str, output_dir: str) -> str:
    """Download audio only. Returns path to .mp3 file."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_download_audio, url, output_dir)


def _resolve_redirect(url: str, timeout: int = 10) -> str:
    """Follow HTTP redirects and return the final URL without downloading the body."""
    import urllib.request
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.url
    except Exception:
        return url


def _sync_probe(url: str) -> str:
    """Resolve URL redirects then check the final URL. Returns 'photo' or 'video'."""
    from helper.link_parser import is_photo_url
    final_url = _resolve_redirect(url)
    if is_photo_url(final_url):
        return "photo"
    return "video"


async def probe_url(url: str) -> str:
    """Async wrapper for _sync_probe. Returns 'photo' or 'video'."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_probe, url)


async def download_video(url: str, quality: str, output_dir: str) -> tuple[list[str], str]:
    """Download a TikTok video or photo post.

    Returns (file_paths, content_type) where content_type is 'video' or 'photo'.
    - video: list of mp4 paths (split if large)
    - photo: list of image paths to send as album
    """
    loop = asyncio.get_event_loop()

    # Short-circuit: skip yt-dlp entirely for known photo/slideshow URLs
    if is_photo_url(url):
        photos = await loop.run_in_executor(None, _sync_download_photos_gdl, url, output_dir)
        if photos:
            return photos, "photo"

    try:
        filepath, info = await loop.run_in_executor(None, _sync_download, url, quality, output_dir)
    except yt_dlp.utils.DownloadError as exc:
        err_str = str(exc)
        if "No video formats found" in err_str or "Unsupported URL" in err_str:
            logger.info("yt-dlp cannot handle this URL (%s) — falling back to gallery-dl", exc)
            photos = await loop.run_in_executor(None, _sync_download_photos_gdl, url, output_dir)
            if photos:
                return photos, "photo"
        raise

    # Detect photo slideshow — yt-dlp downloads images instead of a video
    ext = os.path.splitext(filepath)[1].lower()
    if ext in _IMAGE_EXTS or not os.path.exists(filepath):
        video_id = info.get("id", "")
        photos = _collect_photo_files(output_dir, video_id)
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
