import glob
import logging
import os
import yt_dlp

from config.settings import settings
from core.models import AudioMetadata
from helper.file_utils import resolve_mp4_path
from services.media.binary_resolver import get_ffmpeg_dir
from services.media.thumbnail_service import save_audio_thumbnail

logger = logging.getLogger(__name__)

_HEIGHT_MAP = {"1080p": "1080", "1440p": "1440", "2160p": "2160"}


def build_base_opts(output_dir: str) -> dict:
    """Common yt-dlp options shared by all download modes."""
    opts: dict = {
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": 30,
        "ffmpeg_location": get_ffmpeg_dir(),
    }
    if settings.cookies_file and os.path.isfile(settings.cookies_file):
        opts["cookiefile"] = settings.cookies_file
    return opts


def build_video_opts(quality: str, output_dir: str) -> dict:
    height = _HEIGHT_MAP.get(quality, "1080")
    fmt = (
        f"bestvideo[height<={height}][ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]"
        f"/bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]"
        f"/bestvideo[height<={height}]+bestaudio"
        f"/best[height<={height}][ext=mp4]"
        f"/best[ext=mp4]/best"
    )
    opts = build_base_opts(output_dir)
    opts["format"] = fmt
    opts["merge_output_format"] = "mp4"
    opts["postprocessor_args"] = {"Merger+ffmpeg_o": ["-movflags", "+faststart"]}
    return opts


def build_audio_opts(output_dir: str) -> dict:
    opts = build_base_opts(output_dir)
    opts["format"] = "bestaudio/best"
    ff_loc = get_ffmpeg_dir()
    if ff_loc:
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    opts["outtmpl"] = os.path.join(output_dir, "%(id)s.%(ext)s")
    return opts


def sync_download_video(url: str, quality: str, output_dir: str) -> tuple[str, dict]:
    """Blocking video/photo download using yt-dlp. Returns (raw_path, info)."""
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = build_video_opts(quality, output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        raw_path = ydl.prepare_filename(info)
    return resolve_mp4_path(raw_path), info


def sync_download_audio(url: str, output_dir: str) -> AudioMetadata:
    """Blocking audio extraction using yt-dlp."""
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = build_audio_opts(output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
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
            thumb_path = save_audio_thumbnail(thumb_url, target_thumb)

        return AudioMetadata(
            path=mp3_path,
            title=title,
            performer=performer,
            duration=duration,
            thumbnail_path=thumb_path,
        )
