import os
import json
import asyncio
import logging

import yt_dlp

import config

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
    }
    if config.COOKIES_FILE and os.path.isfile(config.COOKIES_FILE):
        opts["cookiefile"] = config.COOKIES_FILE
    return opts


def _sync_download(url: str, quality: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = _build_ydl_opts(quality, output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # Ensure .mp4 extension after merge
        base, _ = os.path.splitext(filename)
        mp4_path = base + ".mp4"
        if os.path.exists(mp4_path):
            return mp4_path
        return filename


async def download_video(url: str, quality: str, output_dir: str) -> list[str]:
    """Download a TikTok video. Returns list of file paths (multiple if split)."""
    loop = asyncio.get_event_loop()
    filepath = await loop.run_in_executor(None, _sync_download, url, quality, output_dir)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Downloaded file not found: {filepath}")

    file_size = os.path.getsize(filepath)
    if file_size > config.MAX_FILE_SIZE_BYTES:
        logger.info("File %.1f MB > limit, splitting: %s", file_size / 1024 / 1024, filepath)
        parts = await split_video(filepath, config.MAX_FILE_SIZE_BYTES)
        try:
            os.remove(filepath)
        except OSError:
            pass
        return parts

    return [filepath]


async def split_video(filepath: str, max_bytes: int) -> list[str]:
    """Split a video into parts using FFmpeg, each under max_bytes."""
    # Get duration via ffprobe
    probe_cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        filepath,
    ]
    proc = await asyncio.create_subprocess_exec(
        *probe_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

    info = json.loads(stdout)
    duration = float(info["format"]["duration"])
    file_size = os.path.getsize(filepath)

    # Calculate how many chunks we need
    num_parts = max(2, -(-file_size // max_bytes))  # ceiling division
    chunk_duration = duration / num_parts

    base, _ = os.path.splitext(filepath)
    parts: list[str] = []

    for i in range(num_parts):
        start = i * chunk_duration
        output = f"{base}_part{i + 1:02d}.mp4"
        cmd = [
            "ffmpeg",
            "-ss", str(start),
            "-i", filepath,
            "-t", str(chunk_duration),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-y",
            "-loglevel", "quiet",
            output,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("ffmpeg split part %d failed: %s", i + 1, stderr.decode())
            continue
        if os.path.exists(output) and os.path.getsize(output) > 0:
            parts.append(output)

    return parts


def cleanup_files(paths: list[str]) -> None:
    """Delete downloaded/split files after sending."""
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass
