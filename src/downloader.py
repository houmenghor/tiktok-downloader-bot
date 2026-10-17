import asyncio
from dataclasses import dataclass
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


@dataclass
class AudioMetadata:
    path: str
    title: str = ""
    performer: str = ""
    duration: int = 0
    thumbnail_path: str | None = None


def _get_ffmpeg_location() -> str | None:
    import sys
    path = settings.ffmpeg_path or "ffmpeg"
    if sys.platform != "win32" and path.lower().endswith(".exe"):
        path = shutil.which("ffmpeg") or "ffmpeg"
    resolved = shutil.which(path) or path
    if os.path.isfile(resolved):
        return os.path.dirname(resolved)
    if os.path.isdir(resolved):
        return resolved
    return None


def _base_opts(output_dir: str) -> dict:
    """Common yt-dlp options shared by all download modes."""
    opts: dict = {
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": 30,
        "ffmpeg_location": _get_ffmpeg_location(),
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
    ff_loc = _get_ffmpeg_location()
    if ff_loc:
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


def _save_thumbnail(cover_url: str, output_path: str) -> str | None:
    """Download cover image, resize/convert to 320x320 JPEG for Telegram audio player."""
    if cover_url.startswith("/"):
        cover_url = f"https://www.tikwm.com{cover_url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
    }

    data = None
    try:
        import httpx
        with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
            resp = client.get(cover_url)
            if resp.status_code == 200:
                data = resp.content
    except Exception as e:
        logger.debug("httpx thumbnail download failed: %s", e)

    if data is None:
        import urllib.request
        try:
            req = urllib.request.Request(cover_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
        except Exception as e:
            logger.warning("Failed to save audio thumbnail from %s: %s", cover_url, e)
            return None

    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((320, 320))
        img.save(output_path, "JPEG", quality=85)
        return output_path
    except Exception:
        with open(output_path, "wb") as f:
            f.write(data)
        return output_path


def _sync_download_audio(url: str, output_dir: str) -> AudioMetadata:
    """Blocking audio extraction. Returns AudioMetadata."""
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = _build_audio_opts(output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # After postprocessor, file is .mp3
        base = os.path.join(output_dir, info["id"])
        mp3_path = base + ".mp3"
        if not os.path.exists(mp3_path):
            matches = glob.glob(base + "*")
            audio_matches = [
                m for m in matches
                if os.path.splitext(m)[1].lower() in {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus"}
            ]
            if audio_matches:
                mp3_path = audio_matches[0]
            elif matches:
                mp3_path = matches[0]
            else:
                raise FileNotFoundError(f"Audio file not found after download: {base}")

        title = info.get("track") or info.get("title") or "TikTok Audio"
        performer = info.get("artist") or info.get("creator") or info.get("uploader") or "TikTok"
        duration = int(info.get("duration") or 0)

        thumb_path = None
        thumb_url = info.get("thumbnail")
        if thumb_url:
            target_thumb = os.path.join(output_dir, f"{info['id']}_thumb.jpg")
            thumb_path = _save_thumbnail(thumb_url, target_thumb)

        return AudioMetadata(
            path=mp3_path,
            title=title,
            performer=performer,
            duration=duration,
            thumbnail_path=thumb_path,
        )


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


def _fetch_tikwm_data(url: str) -> dict:
    """Robust TikWM API fetcher with browser headers, POST+GET fallback, and httpx/urllib fallback."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.tikwm.com/",
    }

    url_candidates = [url]
    if "?" in url:
        url_candidates.append(url.split("?")[0])

    api_hosts = ["https://www.tikwm.com/api/", "https://tikwm.com/api/"]

    # 1. Try httpx (HTTP/2 + modern TLS ciphers)
    try:
        import httpx
        with httpx.Client(headers=headers, timeout=20.0, follow_redirects=True) as client:
            for host in api_hosts:
                for target_url in url_candidates:
                    # Try POST
                    try:
                        resp = client.post(host, data={"url": target_url, "count": 12, "cursor": 0, "web": 1, "hd": 1})
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("code") == 0 and "data" in data:
                                return data["data"]
                    except Exception as e:
                        logger.debug("TikWM POST via httpx failed (%s): %s", host, e)

                    # Try GET
                    try:
                        resp = client.get(host, params={"url": target_url})
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("code") == 0 and "data" in data:
                                return data["data"]
                    except Exception as e:
                        logger.debug("TikWM GET via httpx failed (%s): %s", host, e)
    except ImportError:
        pass

    # 2. Fallback to urllib with browser headers
    import urllib.request
    import urllib.parse
    import json

    for host in api_hosts:
        for target_url in url_candidates:
            # Try POST
            try:
                post_data = urllib.parse.urlencode({"url": target_url, "count": 12, "cursor": 0, "web": 1, "hd": 1}).encode()
                req = urllib.request.Request(host, data=post_data, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("code") == 0 and "data" in data:
                        return data["data"]
            except Exception as e:
                logger.debug("TikWM POST via urllib failed (%s): %s", host, e)

            # Try GET
            try:
                encoded_url = urllib.parse.quote(target_url, safe="")
                req = urllib.request.Request(f"{host}?url={encoded_url}", headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("code") == 0 and "data" in data:
                        return data["data"]
            except Exception as e:
                logger.debug("TikWM GET via urllib failed (%s): %s", host, e)

    raise RuntimeError("TikWM API failed")


def _download_file(file_url: str, output_path: str, timeout: int = 30) -> None:
    """Download a remote file using httpx or urllib, handling relative URLs and redirects."""
    if file_url.startswith("/"):
        file_url = f"https://www.tikwm.com{file_url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
    }

    try:
        import httpx
        with httpx.Client(headers=headers, timeout=float(timeout), follow_redirects=True) as client:
            resp = client.get(file_url)
            if resp.status_code == 200 and len(resp.content) > 0:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return
    except Exception as e:
        logger.debug("httpx download failed for %s: %s", file_url, e)

    import urllib.request
    req = urllib.request.Request(file_url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(output_path, "wb") as f:
        f.write(resp.read())


def _sync_download_audio_tikwm(url: str, output_dir: str) -> AudioMetadata:
    """Fallback audio downloader using TikWM API. Returns AudioMetadata."""
    import time
    import os

    os.makedirs(output_dir, exist_ok=True)
    post_data = _fetch_tikwm_data(url)

    music_info = post_data.get("music_info") or {}
    # Prefer direct TikTok CDN play link over relative proxy link
    music_url = music_info.get("play") or post_data.get("music")
    if not music_url:
        raise RuntimeError("No audio track found in this post.")

    video_id = post_data.get("id", str(int(time.time())))
    music_path = os.path.join(output_dir, f"{video_id}.mp3")

    try:
        _download_file(music_url, music_path, timeout=30)
    except Exception as e:
        logger.error("Failed to download music %s: %s", music_url, e)
        raise RuntimeError("The post is unavailable. It may have been deleted, set to private, or region-locked by the creator.")

    title = music_info.get("title") or post_data.get("title") or "TikTok Audio"
    performer = music_info.get("author") or (post_data.get("author") or {}).get("nickname") or "TikTok"
    duration = int(music_info.get("duration") or post_data.get("duration") or 0)

    thumb_path = None
    cover_url = (
        music_info.get("cover")
        or (post_data.get("images")[0] if post_data.get("images") else None)
        or (post_data.get("author") or {}).get("avatar")
        or post_data.get("cover")
    )
    if cover_url:
        target_thumb = os.path.join(output_dir, f"{video_id}_thumb.jpg")
        thumb_path = _save_thumbnail(cover_url, target_thumb)

    return AudioMetadata(
        path=music_path,
        title=title,
        performer=performer,
        duration=duration,
        thumbnail_path=thumb_path,
    )


async def download_audio(url: str, output_dir: str) -> AudioMetadata:
    """Download audio only with rich metadata. Returns AudioMetadata."""
    import re
    loop = asyncio.get_event_loop()
    resolved_url = await loop.run_in_executor(None, _resolve_redirect, url)

    # For photo slideshow URLs, TikTok serves the underlying audio track under /video/<id>
    # e.g. https://www.tiktok.com/@user/photo/123 -> https://www.tiktok.com/@user/video/123
    clean_resolved = resolved_url.split("?")[0]
    ytdlp_audio_url = re.sub(r"/photo/", "/video/", clean_resolved) if is_photo_url(resolved_url) else url

    if is_photo_url(resolved_url):
        try:
            return await loop.run_in_executor(None, _sync_download_audio_tikwm, resolved_url, output_dir)
        except Exception as exc:
            logger.info("TikWM failed for photo post audio (%s) — trying yt-dlp fallback with %s", exc, ytdlp_audio_url)
            return await loop.run_in_executor(None, _sync_download_audio, ytdlp_audio_url, output_dir)
    try:
        return await loop.run_in_executor(None, _sync_download_audio, ytdlp_audio_url, output_dir)
    except Exception as exc:
        logger.info("yt-dlp failed to download audio (%s) — falling back to TikWM", exc)
        return await loop.run_in_executor(None, _sync_download_audio_tikwm, resolved_url, output_dir)


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
    import time
    os.makedirs(output_dir, exist_ok=True)

    try:
        post_data = _fetch_tikwm_data(url)
    except Exception as e:
        logger.error("TikWM API failed: %s", e)
        return [], ""

    video_id = post_data.get("id", str(int(time.time())))

    if post_data.get("images"):
        photos = []
        for i, img_url in enumerate(post_data["images"]):
            ext = img_url.split("?")[0].split(".")[-1]
            if len(ext) > 4:
                ext = "jpg"
            img_path = os.path.join(output_dir, f"{video_id}_{i}.{ext}")
            try:
                _download_file(img_url, img_path, timeout=20)
                photos.append(img_path)
            except Exception as e:
                logger.error("Failed to download image %s: %s", img_url, e)
        if photos:
            return photos, "photo"

    elif post_data.get("play"):
        video_url = post_data.get("hdplay") or post_data.get("play")
        vid_path = os.path.join(output_dir, f"{video_id}.mp4")
        try:
            _download_file(video_url, vid_path, timeout=45)
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
