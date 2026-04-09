import re

# Matches all TikTok link formats:
#   https://www.tiktok.com/@user/video/123
#   https://vm.tiktok.com/ABC123/
#   https://vt.tiktok.com/ABC123/
_TIKTOK_PATTERN = re.compile(
    r"https?://(?:www\.|vm\.|vt\.)?tiktok\.com/\S+",
    re.IGNORECASE,
)


def extract_links(text: str) -> list[str]:
    """Extract all unique TikTok URLs from a block of text or a file's contents.

    Algorithm: single-pass regex findall → deduplicate while preserving order
    using dict.fromkeys (O(n) time, O(n) space).
    """
    raw = _TIKTOK_PATTERN.findall(text)
    # Strip trailing punctuation that could be attached (e.g. "url,")
    cleaned = [_strip_trailing(link) for link in raw]
    # Deduplicate preserving insertion order
    unique = list(dict.fromkeys(cleaned))
    return unique


def _strip_trailing(url: str) -> str:
    """Remove trailing punctuation characters that are not part of a URL."""
    return url.rstrip(".,;:!?\"')")


_PHOTO_PATTERN = re.compile(r"/photo/\d+", re.IGNORECASE)


def is_photo_url(url: str) -> bool:
    """Return True if the URL points to a TikTok photo/slideshow post."""
    return bool(_PHOTO_PATTERN.search(url))
