import logging
import os
import re
import urllib.request
import yt_dlp

from services.bypass.base import download_remote_file

logger = logging.getLogger(__name__)


def resolve_redirect(url: str, timeout: int = 10) -> str:
    """Follow HTTP redirects and return the final resolved URL."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.url
    except Exception:
        return url


def download_photos_ytdlp_native(url: str, output_dir: str) -> list[str]:
    """Extract and download all full-resolution photo slideshow images using yt-dlp native web extractor."""
    os.makedirs(output_dir, exist_ok=True)
    resolved_url = resolve_redirect(url)
    clean_url = resolved_url.split("?")[0]
    video_url = re.sub(r"/photo/", "/video/", clean_url)

    try:
        ydl = yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True})
        ie = ydl.get_info_extractor("TikTok")
        match = ie._match_valid_url(video_url)
        if not match:
            return []
        video_id = match.group("id")
        user_id = match.group("user_id")
        target_url = ie._create_url(user_id, video_id)

        video_data, status = ie._extract_web_data_and_status(target_url, video_id)
        if not video_data or status != 0:
            return []

        images = video_data.get("imagePost", {}).get("images", [])
        downloaded = []
        for idx, img in enumerate(images):
            url_list = img.get("imageURL", {}).get("urlList", [])
            if not url_list:
                continue
            img_url = url_list[0]
            out_file = os.path.join(output_dir, f"{video_id}_{idx}.jpg")
            try:
                download_remote_file(img_url, out_file, timeout=20)
                if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                    downloaded.append(out_file)
            except Exception as e:
                logger.error("Failed to download slideshow photo %s: %s", img_url, e)

        # Fallback to single cover image if images list was empty
        if not downloaded:
            cover_list = video_data.get("imagePost", {}).get("cover", {}).get("imageURL", {}).get("urlList", [])
            if cover_list:
                out_file = os.path.join(output_dir, f"{video_id}_0.jpg")
                download_remote_file(cover_list[0], out_file, timeout=20)
                if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                    downloaded.append(out_file)

        return downloaded
    except Exception as exc:
        logger.debug("yt-dlp native photo extraction failed: %s", exc)
        return []
