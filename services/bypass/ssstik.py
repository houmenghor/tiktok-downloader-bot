import base64
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

from core.models import AudioMetadata
from services.bypass.base import download_remote_file
from services.media.audio_processor import probe_audio_duration
from services.media.thumbnail_service import save_audio_thumbnail

logger = logging.getLogger(__name__)


def fetch_ssstik_html(url: str) -> str:
    """Fetch parsed response from ssstik.io to bypass TikTok age/content gates."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ssstik.io/en",
    }
    data = urllib.parse.urlencode({"id": url, "locale": "en", "tt": "0"}).encode()
    req = urllib.request.Request("https://ssstik.io/abc?url=dl", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="ignore")


def download_photos_ssstik(url: str, output_dir: str) -> list[str]:
    """Extract and download slideshow images from ssstik."""
    os.makedirs(output_dir, exist_ok=True)
    try:
        html = fetch_ssstik_html(url)
    except Exception as e:
        logger.debug("ssstik HTML fetch failed: %s", e)
        return []

    # 1. From splide lazy-load attributes
    b64_matches = re.findall(r'data-splide-lazy=["\']https://tikcdn\.io/ssstik/s/([^"\']+)["\']', html)
    # 2. Check direct download button links if splide empty
    if not b64_matches:
        b64_matches = re.findall(r'href=["\']https://tikcdn\.io/ssstik/(?:s/)?([A-Za-z0-9+/=]+)["\'][^>]*class=["\'][^"\']*slide', html)

    slide_urls: list[str] = []
    for b in b64_matches:
        try:
            padded = b + "=" * (-len(b) % 4)
            decoded = base64.b64decode(padded).decode("utf-8")
            if decoded.startswith("http") and decoded not in slide_urls:
                slide_urls.append(decoded)
        except Exception:
            pass

    if not slide_urls:
        return []

    video_id = str(int(time.time()))
    id_match = re.search(r'/(?:photo|video)/(\d+)', url)
    if id_match:
        video_id = id_match.group(1)

    downloaded = []
    for idx, img_url in enumerate(slide_urls):
        ext = "webp" if ".webp" in img_url.lower() else "jpg"
        out_file = os.path.join(output_dir, f"{video_id}_{idx}.{ext}")
        try:
            download_remote_file(img_url, out_file, timeout=20)
            if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                downloaded.append(out_file)
        except Exception as e:
            logger.error("Failed to download ssstik slide photo %s: %s", img_url, e)

    return downloaded


def download_audio_ssstik(url: str, output_dir: str) -> AudioMetadata:
    """Extract and download MP3 audio stream from ssstik."""
    os.makedirs(output_dir, exist_ok=True)
    html = fetch_ssstik_html(url)

    mp3_b64 = re.findall(r'href=["\']https://tikcdn\.io/ssstik/m/([^"\']+)["\']', html)
    if not mp3_b64:
        raise RuntimeError("No audio track found on ssstik.")

    padded = mp3_b64[0] + "=" * (-len(mp3_b64[0]) % 4)
    music_url = base64.b64decode(padded).decode("utf-8")

    video_id = str(int(time.time()))
    id_match = re.search(r'/(?:photo|video)/(\d+)', url)
    if id_match:
        video_id = id_match.group(1)

    music_path = os.path.join(output_dir, f"{video_id}.mp3")
    download_remote_file(music_url, music_path, timeout=30)
    if not os.path.exists(music_path) or os.path.getsize(music_path) == 0:
        raise RuntimeError("Downloaded audio file is empty from ssstik.")

    soup = BeautifulSoup(html, "html.parser")
    h2 = soup.find("h2")
    author_name = h2.get_text(strip=True) if h2 else "TikTok"

    cover_url = None
    avatar = soup.find("img", class_="result_author") or soup.select_one("#avatar_and_text img")
    if avatar:
        src = avatar.get("src") or avatar.get("data-splide-lazy")
        if src and "tikcdn.io/ssstik/a/" in src:
            try:
                b_part = src.split("tikcdn.io/ssstik/a/")[-1]
                padded_b = b_part + "=" * (-len(b_part) % 4)
                cover_url = base64.b64decode(padded_b).decode("utf-8")
            except Exception:
                cover_url = src

    if not cover_url:
        b64_slides = re.findall(r'data-splide-lazy=["\']https://tikcdn\.io/ssstik/s/([^"\']+)["\']', html)
        if b64_slides:
            try:
                padded_b = b64_slides[0] + "=" * (-len(b64_slides[0]) % 4)
                cover_url = base64.b64decode(padded_b).decode("utf-8")
            except Exception:
                pass

    thumb_path = None
    if cover_url:
        target_thumb = os.path.join(output_dir, f"{video_id}_thumb.jpg")
        thumb_path = save_audio_thumbnail(cover_url, target_thumb)

    duration = probe_audio_duration(music_path)

    return AudioMetadata(
        path=music_path,
        title="TikTok Audio",
        performer=author_name,
        duration=duration,
        thumbnail_path=thumb_path,
    )
