import json
import logging
import os
import time
import urllib.parse
import urllib.request

from core.models import AudioMetadata
from services.bypass.base import download_remote_file
from services.media.thumbnail_service import save_audio_thumbnail

logger = logging.getLogger(__name__)


def fetch_tikwm_data(url: str) -> dict:
    """Robust TikWM API fetcher with browser headers, POST+GET fallback, and httpx/urllib."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.tikwm.com/",
    }

    url_candidates = [url]
    if "?" in url:
        url_candidates.append(url.split("?")[0])

    api_hosts = ["https://www.tikwm.com/api/", "https://tikwm.com/api/"]

    try:
        import httpx
        with httpx.Client(headers=headers, timeout=20.0, follow_redirects=True) as client:
            for host in api_hosts:
                for target_url in url_candidates:
                    try:
                        resp = client.post(host, data={"url": target_url, "count": 12, "cursor": 0, "web": 1, "hd": 1})
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("code") == 0 and "data" in data:
                                return data["data"]
                    except Exception as e:
                        logger.debug("TikWM POST via httpx failed (%s): %s", host, e)

                    try:
                        resp = client.get(host, params={"url": target_url})
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("code") == 0 and "data" in data:
                                return data["data"]
                    except Exception as e:
                        logger.debug("TikWM GET via httpx failed (%s): %s", host, e)
    except ImportError:
        pass

    for host in api_hosts:
        for target_url in url_candidates:
            try:
                post_data = urllib.parse.urlencode({"url": target_url, "count": 12, "cursor": 0, "web": 1, "hd": 1}).encode()
                req = urllib.request.Request(host, data=post_data, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("code") == 0 and "data" in data:
                        return data["data"]
            except Exception as e:
                logger.debug("TikWM POST via urllib failed (%s): %s", host, e)

            try:
                encoded_url = urllib.parse.quote(target_url, safe="")
                req = urllib.request.Request(f"{host}?url={encoded_url}", headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("code") == 0 and "data" in data:
                        return data["data"]
            except Exception as e:
                logger.debug("TikWM GET via urllib failed (%s): %s", host, e)

    raise RuntimeError("TikWM API failed")


def download_photos_tikwm(url: str, output_dir: str) -> tuple[list[str], str]:
    """Download photos or video using TikWM API."""
    os.makedirs(output_dir, exist_ok=True)
    try:
        post_data = fetch_tikwm_data(url)
    except Exception as e:
        logger.error("TikWM API failed: %s", e)
        return [], ""

    video_id = post_data.get("id", str(int(time.time())))

    if post_data.get("images"):
        photos = []
        for i, img_url in enumerate(post_data["images"]):
            ext = img_url.split("?")[0].split(".")[-1]
            if len(ext) > 4:
                ext = "jpg"
            img_path = os.path.join(output_dir, f"{video_id}_{i}.{ext}")
            try:
                download_remote_file(img_url, img_path, timeout=20)
                photos.append(img_path)
            except Exception as e:
                logger.error("Failed to download image %s: %s", img_url, e)
        if photos:
            return photos, "photo"

    elif post_data.get("play"):
        video_url = post_data.get("hdplay") or post_data.get("play")
        vid_path = os.path.join(output_dir, f"{video_id}.mp4")
        try:
            download_remote_file(video_url, vid_path, timeout=45)
            return [vid_path], "video"
        except Exception as e:
            logger.error("Failed to download video %s: %s", video_url, e)

    return [], ""


def download_audio_tikwm(url: str, output_dir: str) -> AudioMetadata:
    """Download audio using TikWM API."""
    os.makedirs(output_dir, exist_ok=True)
    post_data = fetch_tikwm_data(url)

    music_info = post_data.get("music_info") or {}
    music_url = music_info.get("play") or post_data.get("music")
    if not music_url:
        raise RuntimeError("No audio track found in TikWM post.")

    video_id = post_data.get("id", str(int(time.time())))
    music_path = os.path.join(output_dir, f"{video_id}.mp3")

    download_remote_file(music_url, music_path, timeout=30)

    title = music_info.get("title") or post_data.get("title") or "TikTok Audio"
    performer = music_info.get("author") or (post_data.get("author") or {}).get("nickname") or "TikTok"
    duration = int(music_info.get("duration") or post_data.get("duration") or 0)

    thumb_path = None
    cover_url = (
        music_info.get("cover")
        or (post_data.get("images")[0] if post_data.get("images") else None)
        or (post_data.get("author") or {}).get("avatar")
        or post_data.get("cover")
    )
    if cover_url:
        target_thumb = os.path.join(output_dir, f"{video_id}_thumb.jpg")
        thumb_path = save_audio_thumbnail(cover_url, target_thumb)

    return AudioMetadata(
        path=music_path,
        title=title,
        performer=performer,
        duration=duration,
        thumbnail_path=thumb_path,
    )
