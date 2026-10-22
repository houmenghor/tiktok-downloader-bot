"""
Downloader facade re-exporting services for backward compatibility.
All logic is now cleanly separated in:
- services/downloader/ (yt-dlp engine & download service)
- services/bypass/ (SSSTik, TikWM, Native Web, Gallery-dl bypass modules)
- services/media/ (audio duration, thumbnails, video splitting)
- core/models.py (Req/Res contracts: AudioMetadata, MediaResult)
"""
from core.models import AudioMetadata, MediaResult
from services.downloader.download_service import (
    download_video,
    download_audio,
    probe_url,
    sync_probe,
)
from services.bypass.manager import get_bypass_strategies

__all__ = [
    "download_video",
    "download_audio",
    "probe_url",
    "sync_probe",
    "AudioMetadata",
    "MediaResult",
    "get_bypass_strategies",
]
