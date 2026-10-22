import logging
import os
import urllib.request

logger = logging.getLogger(__name__)


def download_remote_file(file_url: str, output_path: str, timeout: int = 30) -> None:
    """Download a remote file using httpx or urllib, handling relative URLs and redirects."""
    if file_url.startswith("/"):
        file_url = f"https://www.tikwm.com{file_url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
    }

    try:
        import httpx
        with httpx.Client(headers=headers, timeout=float(timeout), follow_redirects=True) as client:
            resp = client.get(file_url)
            if resp.status_code == 200 and len(resp.content) > 0:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return
    except Exception as e:
        logger.debug("httpx download failed for %s: %s", file_url, e)

    req = urllib.request.Request(file_url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(output_path, "wb") as f:
        f.write(resp.read())
