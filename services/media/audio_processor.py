import json
import logging
import subprocess
from services.media.binary_resolver import get_ffprobe_cmd

logger = logging.getLogger(__name__)


def probe_audio_duration(filepath: str) -> int:
    """Use ffprobe to get audio/video duration in integer seconds."""
    ffprobe_cmd = get_ffprobe_cmd()
    try:
        cmd = [ffprobe_cmd, "-v", "quiet", "-print_format", "json", "-show_format", filepath]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            return int(float(data.get("format", {}).get("duration", 0)))
    except Exception as e:
        logger.debug("ffprobe duration failed on %s: %s", filepath, e)
    return 0
