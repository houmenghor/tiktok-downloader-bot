import io
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)


def save_audio_thumbnail(cover_url: str, output_path: str) -> str | None:
    """Download cover image, resize/convert to 320x320 JPEG for Telegram native audio player."""
    if cover_url.startswith("/"):
        cover_url = f"https://www.tikwm.com{cover_url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
    }

    data: bytes | None = None
    try:
        import httpx
        with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
            resp = client.get(cover_url)
            if resp.status_code == 200:
                data = resp.content
    except Exception as e:
        logger.debug("httpx thumbnail download failed: %s", e)

    if data is None:
        try:
            req = urllib.request.Request(cover_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
        except Exception as e:
            logger.warning("Failed to save audio thumbnail from %s: %s", cover_url, e)
            return None

    try:
        from PIL import Image
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
