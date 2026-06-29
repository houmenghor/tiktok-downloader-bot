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


def _sync_download_audio_tikwm(url: str, output_dir: str) -> str:
    """Fallback audio downloader using TikWM API."""
    import urllib.request
    import json
    import time
    import os

    os.makedirs(output_dir, exist_ok=True)
    api_url = f"https://www.tikwm.com/api/?url={url}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        logger.error("TikWM API failed for audio: %s", e)
        raise RuntimeError("TikWM API failed")

    if data.get("code") != 0 or "data" not in data or not data["data"].get("music"):
        logger.error("TikWM API returned error or no music: %s", data)
        raise RuntimeError("The post is unavailable. It may have been deleted, set to private, or region-locked by the creator.")

    music_url = data["data"]["music"]
    video_id = data["data"].get("id", str(int(time.time())))
    music_req = urllib.request.Request(music_url, headers={"User-Agent": "Mozilla/5.0"})
    music_path = os.path.join(output_dir, f"{video_id}.mp3")
    try:
        with urllib.request.urlopen(music_req, timeout=30) as m_resp, open(music_path, "wb") as f:
            f.write(m_resp.read())
        return music_path
    except Exception as e:
        logger.error("Failed to download music %s: %s", music_url, e)
        raise RuntimeError("The post is unavailable. It may have been deleted, set to private, or region-locked by the creator.")

async def download_audio(url: str, output_dir: str) -> str:
    """Download audio only. Returns path to .mp3 file."""
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, _sync_download_audio, url, output_dir)
    except Exception as exc:
        logger.info("yt-dlp failed to download audio (%s) — falling back to TikWM", exc)
        return await loop.run_in_executor(None, _sync_download_audio_tikwm, url, output_dir)


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


def _sync_download_tikwm(url: str, output_dir: str) -> tuple[list[str], str]:
    """Fallback downloader using TikWM API."""
    import urllib.request
    import json
    import time

    os.makedirs(output_dir, exist_ok=True)
    api_url = f"https://www.tikwm.com/api/?url={url}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        logger.error("TikWM API failed: %s", e)
        return [], ""

    if data.get("code") != 0 or "data" not in data:
        logger.error("TikWM API returned error: %s", data)
        return [], ""

    post_data = data["data"]
    video_id = post_data.get("id", str(int(time.time())))

    if post_data.get("images"):
        photos = []
        for i, img_url in enumerate(post_data["images"]):
            img_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
            ext = img_url.split("?")[0].split(".")[-1]
            if len(ext) > 4: ext = "jpg"
            img_path = os.path.join(output_dir, f"{video_id}_{i}.{ext}")
            try:
                with urllib.request.urlopen(img_req, timeout=15) as img_resp, open(img_path, "wb") as f:
                    f.write(img_resp.read())
                photos.append(img_path)
            except Exception as e:
                logger.error("Failed to download image %s: %s", img_url, e)
        if photos:
            return photos, "photo"

    elif post_data.get("play"):
        video_url = post_data.get("hdplay") or post_data.get("play")
        vid_req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
        vid_path = os.path.join(output_dir, f"{video_id}.mp4")
        try:
            with urllib.request.urlopen(vid_req, timeout=30) as vid_resp, open(vid_path, "wb") as f:
                f.write(vid_resp.read())
            return [vid_path], "video"
        except Exception as e:
            logger.error("Failed to download video %s: %s", video_url, e)

    return [], ""


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
        # If yt-dlp only downloaded audio (due to anti-bot restrictions), force the fallback
        if os.path.splitext(filepath)[1].lower() in {".mp3", ".m4a", ".wav", ".aac", ".weba"}:
            raise RuntimeError("yt-dlp returned an audio file instead of a video (bot protection)")
    except Exception as exc:
        err_str = str(exc)
        logger.info("yt-dlp failed (%s) — falling back to gallery-dl", exc)
        photos = await loop.run_in_executor(None, _sync_download_photos_gdl, url, output_dir)
        if photos:
            return photos, "photo"
        logger.info("gallery-dl also failed, falling back to TikWM API")
        tikwm_files, kind = await loop.run_in_executor(None, _sync_download_tikwm, url, output_dir)
        if tikwm_files:
            return tikwm_files, kind
        raise RuntimeError("The post is unavailable. It may have been deleted, set to private, or region-locked by the creator.")

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
