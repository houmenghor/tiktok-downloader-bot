import asyncio
import json
import logging
import os

from config.settings import settings

logger = logging.getLogger(__name__)


async def get_duration(filepath: str) -> float:
    """Use ffprobe to get video duration in seconds."""
    cmd = [
        settings.ffprobe_path, "-v", "quiet",
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
    """Split *filepath* into chunks where each chunk is ≤ max_bytes.

    Algorithm:
      1. Get total duration via ffprobe.
      2. Calculate num_parts = ceil(file_size / max_bytes).
      3. Divide duration evenly → chunk_duration per part.
      4. Use `ffmpeg -ss <start> -t <duration> -c copy` for fast, lossless splits.

    Returns a list of output file paths (in order).
    """
    file_size = os.path.getsize(filepath)
    # Ceiling division
    num_parts = max(2, -(-file_size // max_bytes))
    duration = await get_duration(filepath)
    chunk_duration = duration / num_parts

    base, _ = os.path.splitext(filepath)
    parts: list[str] = []

    for i in range(num_parts):
        start = i * chunk_duration
        output = f"{base}_part{i + 1:02d}.mp4"
        cmd = [
            settings.ffmpeg_path,
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
