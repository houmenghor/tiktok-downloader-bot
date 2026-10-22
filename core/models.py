from dataclasses import dataclass
from enum import Enum


class ContentType(str, Enum):
    VIDEO = "video"
    PHOTO = "photo"
    AUDIO = "audio"


@dataclass
class DownloadRequest:
    url: str
    quality: str = "1080p"
    user_id: int = 0
    chat_id: int = 0
    label: str = ""


@dataclass
class AudioMetadata:
    path: str
    title: str = ""
    performer: str = ""
    duration: int = 0
    thumbnail_path: str | None = None


@dataclass
class MediaResult:
    files: list[str]
    content_type: str  # "video" or "photo"
    title: str = ""
    duration: int = 0


@dataclass
class BypassStrategyInfo:
    id: str
    name: str
    description: str
    target: str
    is_active: bool = True
