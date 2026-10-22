import logging
import os
import shutil
import tempfile

logger = logging.getLogger(__name__)
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def download_photos_gallery_dl(url: str, output_dir: str) -> list[str]:
    """Fallback photo downloader using gallery-dl Python API."""
    import gallery_dl.config
    import gallery_dl.job

    os.makedirs(output_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        gallery_dl.config.set(("extractor",), "base-directory", tmp)
        gallery_dl.config.set(("extractor",), "filename", "{id}_{num}.{extension}")
        try:
            job = gallery_dl.job.DownloadJob(url)
            job.run()
        except Exception as e:
            logger.debug("gallery-dl job run failed: %s", e)
            return []

        photos = []
        for root, _dirs, files in os.walk(tmp):
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext in _IMAGE_EXTS:
                    src = os.path.join(root, fname)
                    dst = os.path.join(output_dir, fname)
                    shutil.move(src, dst)
                    photos.append(dst)
    return sorted(photos)
