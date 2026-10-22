import os
import shutil
import sys

from config.settings import settings


def resolve_binary(path: str | None, default_name: str) -> str:
    """Resolve an executable binary path safely across Windows and Linux."""
    candidate = path or default_name
    if sys.platform != "win32" and candidate.lower().endswith(".exe"):
        candidate = shutil.which(default_name) or default_name
    resolved = shutil.which(candidate) or candidate
    return resolved


def get_ffmpeg_cmd() -> str:
    return resolve_binary(settings.ffmpeg_path, "ffmpeg")


def get_ffprobe_cmd() -> str:
    return resolve_binary(settings.ffprobe_path, "ffprobe")


def get_ffmpeg_dir() -> str | None:
    cmd = get_ffmpeg_cmd()
    if os.path.isfile(cmd):
        return os.path.dirname(cmd)
    if os.path.isdir(cmd):
        return cmd
    return None
