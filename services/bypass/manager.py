import logging
from core.models import AudioMetadata, BypassStrategyInfo
from services.bypass.native_web import download_photos_ytdlp_native
from services.bypass.ssstik import download_photos_ssstik, download_audio_ssstik
from services.bypass.tikwm import download_photos_tikwm, download_audio_tikwm
from services.bypass.gallery_dl_engine import download_photos_gallery_dl

logger = logging.getLogger(__name__)

# Registered bypass strategies
_REGISTERED_STRATEGIES: list[BypassStrategyInfo] = [
    BypassStrategyInfo(
        id="native_web",
        name="TikTok Native Web Extractor",
        description="Directly extracts imagePost data from TikTok web JSON",
        target="Photo Slideshows (Normal Posts)",
        is_active=True,
    ),
    BypassStrategyInfo(
        id="ssstik",
        name="SSSTik Cloud Bypass",
        description="Bypasses age gates, sensitive content warnings, and regional restrictions",
        target="Age-Restricted & Classified Posts + MP3 Streams",
        is_active=True,
    ),
    BypassStrategyInfo(
        id="tikwm",
        name="TikWM Multi-Host API",
        description="Fast multi-host CDN parser for high-definition video, audio & photos",
        target="Fast Video & Audio CDN Streams",
        is_active=True,
    ),
    BypassStrategyInfo(
        id="gallery_dl",
        name="Gallery-dl Engine",
        description="Modular multi-image scraper and downloader",
        target="Complex Multi-Slide Carousels",
        is_active=True,
    ),
]


def get_bypass_strategies() -> list[BypassStrategyInfo]:
    """Return all active bypass strategies and their operational statuses."""
    return _REGISTERED_STRATEGIES


def bypass_download_photos(url: str, output_dir: str) -> tuple[list[str], str]:
    """Execute photo bypass strategy cascade: native_web -> ssstik -> tikwm -> gallery_dl."""
    # 1. Native yt-dlp web extractor
    photos = download_photos_ytdlp_native(url, output_dir)
    if photos:
        logger.info("Photos extracted via Native Web Extractor")
        return photos, "photo"

    # 2. SSSTik bypass (handles age-restricted / sensitive content)
    photos = download_photos_ssstik(url, output_dir)
    if photos:
        logger.info("Photos extracted via SSSTik Bypass")
        return photos, "photo"

    # 3. TikWM fallback
    tikwm_files, kind = download_photos_tikwm(url, output_dir)
    if tikwm_files:
        logger.info("Media extracted via TikWM API (%s)", kind)
        return tikwm_files, kind

    # 4. gallery-dl fallback
    photos = download_photos_gallery_dl(url, output_dir)
    if photos:
        logger.info("Photos extracted via Gallery-dl Engine")
        return photos, "photo"

    return [], ""


def bypass_download_audio(url: str, output_dir: str) -> AudioMetadata:
    """Execute audio bypass cascade: TikWM -> SSSTik."""
    # 1. TikWM
    try:
        return download_audio_tikwm(url, output_dir)
    except Exception as exc_tikwm:
        logger.info("TikWM audio failed (%s) — falling back to SSSTik", exc_tikwm)

    # 2. SSSTik
    try:
        return download_audio_ssstik(url, output_dir)
    except Exception as exc_ssstik:
        logger.error("SSSTik audio bypass failed: %s", exc_ssstik)
        raise RuntimeError("The post is unavailable. It may have been deleted, set to private, or region-locked by the creator.")
