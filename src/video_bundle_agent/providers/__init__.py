from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def detect_platform(source: str) -> str:
    path = Path(source)
    if path.exists():
        return "local_video"

    host = urlparse(source).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "bilibili.com" in host or "b23.tv" in host:
        return "bilibili"
    if "xiaohongshu.com" in host or "xhslink.com" in host:
        return "xiaohongshu"
    return "unsupported"
