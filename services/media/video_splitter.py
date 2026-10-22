import asyncio
import json
import logging
import os

from config.settings import settings
from services.media.binary_resolver import get_ffmpeg_cmd, get_ffprobe_cmd

logger = logging.getLogger(__name__)


async def get_duration(filepath: str) -> float:
    """Use ffprobe to get video duration in seconds."""
    ffprobe_bin = get_ffprobe_cmd()
    cmd = [
        ffprobe_bin, "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        filepath,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode().strip()}")

    data = json.loads(stdout)
    return float(data["format"]["duration"])


async def split_video(filepath: str, max_bytes: int) -> list[str]:
    """Split *filepath* into chunks where each chunk is ≤ max_bytes."""
    file_size = os.path.getsize(filepath)
    num_parts = max(2, -(-file_size // max_bytes))
    duration = await get_duration(filepath)
    chunk_duration = duration / num_parts

    base, _ = os.path.splitext(filepath)
    parts: list[str] = []

    ffmpeg_bin = get_ffmpeg_cmd()
    for i in range(num_parts):
        start = i * chunk_duration
        output = f"{base}_part{i + 1:02d}.mp4"
        cmd = [
            ffmpeg_bin,
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
            logger.warning("ffmpeg split part %d failed: %s", i + 1, stderr.decode().strip())
            continue
        if os.path.exists(output) and os.path.getsize(output) > 0:
            parts.append(output)
            logger.info("Split part %d/%d: %s", i + 1, num_parts, output)

    return parts
