from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from video_bundle_agent.bundle.writer import BundleArtifacts
from video_bundle_agent.diagnostics.models import DiagnosticLog
from video_bundle_agent.providers.url_resolution import DEFAULT_USER_AGENT


def _safe_stem(value: str) -> str:
    stem = re.sub(r"[^0-9A-Za-z._-]+", "-", value).strip(".-")
    return stem[:80] or "video"


def _image_suffix(url: str, content_type: str) -> str:
    path_suffix = Path(urlparse(url).path).suffix.lower()
    if path_suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if path_suffix == ".jpeg" else path_suffix
    content_type = content_type.lower()
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    return ".jpg"


def _normalize_image_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    return url


def attach_thumbnail_asset(
    *,
    metadata: dict[str, object] | None,
    output_dir: Path,
    artifacts: BundleArtifacts,
    diagnostics: DiagnosticLog,
    source_id: str,
    referer: str,
    cookie_string: str = "",
    timeout_seconds: float = 30,
) -> None:
    if not metadata:
        return
    thumbnail = _normalize_image_url(str(metadata.get("thumbnail") or ""))
    if not thumbnail.startswith(("http://", "https://")):
        return

    target_dir = output_dir / "raw" / "thumbnail"
    target_dir.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": referer,
    }
    if cookie_string:
        headers["Cookie"] = cookie_string

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout_seconds,
            headers=headers,
        ) as client:
            response = client.get(thumbnail)
            response.raise_for_status()
        suffix = _image_suffix(thumbnail, response.headers.get("content-type", ""))
        filename = f"{_safe_stem(source_id)}{suffix}"
        path = target_dir / filename
        path.write_bytes(response.content)
    except Exception as error:  # noqa: BLE001
        diagnostics.add(
            code="THUMBNAIL_UNAVAILABLE",
            severity="warning",
            stage="thumbnail",
            message=f"Could not download thumbnail image: {error}",
            details={"thumbnail": thumbnail, "exception": type(error).__name__},
        )
        return

    relative_path = path.relative_to(output_dir).as_posix()
    metadata["thumbnail"] = thumbnail
    metadata["thumbnail_path"] = relative_path
    artifacts.add("thumbnail_path", "thumbnail", relative_path)
