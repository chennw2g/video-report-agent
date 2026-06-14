from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)


@dataclass(frozen=True)
class UrlResolution:
    original_url: str
    working_url: str
    changed: bool
    method: str


def _with_scheme(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def _strip_tracking_query(url: str, *, keep: set[str]) -> str:
    parsed = urlparse(url)
    query = [(key, value) for key, value in parse_qsl(parsed.query) if key in keep]
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query),
            "",
        )
    )


def normalize_youtube_url(source_url: str) -> UrlResolution:
    original = _with_scheme(source_url)
    parsed = urlparse(original)
    host = parsed.netloc.lower()
    video_id = ""
    if host.endswith("youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]
    elif "/shorts/" in parsed.path:
        video_id = parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]
    elif "/embed/" in parsed.path:
        video_id = parsed.path.split("/embed/", 1)[1].split("/", 1)[0]
    elif parsed.path == "/watch":
        query = dict(parse_qsl(parsed.query))
        video_id = query.get("v", "")

    if video_id:
        working = f"https://www.youtube.com/watch?v={video_id}"
        return UrlResolution(
            original_url=source_url,
            working_url=working,
            changed=working != source_url,
            method="youtube_id_normalization",
        )
    working = _strip_tracking_query(original, keep={"v", "list", "index"})
    return UrlResolution(
        original_url=source_url,
        working_url=working,
        changed=working != source_url,
        method="youtube_query_normalization",
    )


def resolve_redirect_url(
    source_url: str,
    *,
    referer: str | None = None,
    cookie_string: str = "",
    timeout_seconds: float = 20,
) -> str:
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    if referer:
        headers["Referer"] = referer
    if cookie_string:
        headers["Cookie"] = cookie_string
    with httpx.Client(follow_redirects=True, timeout=timeout_seconds, headers=headers) as client:
        response = client.get(_with_scheme(source_url))
        response.raise_for_status()
        return str(response.url)


def normalize_bilibili_url(source_url: str) -> UrlResolution:
    original = _with_scheme(source_url)
    parsed = urlparse(original)
    host = parsed.netloc.lower()
    if "b23.tv" in host:
        resolved = resolve_redirect_url(original, referer="https://www.bilibili.com/")
        working = _strip_tracking_query(resolved, keep={"p"})
        return UrlResolution(
            original_url=source_url,
            working_url=working,
            changed=working != source_url,
            method="b23_redirect_resolution",
        )
    working = _strip_tracking_query(original, keep={"p"})
    return UrlResolution(
        original_url=source_url,
        working_url=working,
        changed=working != source_url,
        method="bilibili_query_normalization",
    )


def normalize_xiaohongshu_url(source_url: str, *, cookie_string: str = "") -> UrlResolution:
    original = _with_scheme(source_url)
    parsed = urlparse(original)
    host = parsed.netloc.lower()
    if "xhslink.com" in host:
        resolved = resolve_redirect_url(
            original,
            referer="https://www.xiaohongshu.com/",
            cookie_string=cookie_string,
        )
        return UrlResolution(
            original_url=source_url,
            working_url=resolved,
            changed=resolved != source_url,
            method="xhslink_redirect_resolution",
        )
    return UrlResolution(
        original_url=source_url,
        working_url=original,
        changed=original != source_url,
        method="xiaohongshu_url_normalization",
    )
