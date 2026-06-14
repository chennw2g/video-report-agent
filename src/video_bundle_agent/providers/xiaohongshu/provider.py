from __future__ import annotations

import json
import mimetypes
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from xhs import XhsClient

from video_bundle_agent.bundle.readiness import evaluate_bundle_readiness
from video_bundle_agent.bundle.schema import Capabilities, SourceInfo
from video_bundle_agent.bundle.writer import (
    BundleArtifacts,
    finalize_bundle,
    write_json,
    write_text,
)
from video_bundle_agent.diagnostics.models import DiagnosticLog
from video_bundle_agent.media.ffmpeg import extract_audio_wav
from video_bundle_agent.media.transcription import (
    build_transcript_payload,
    transcribe_audio_for_language,
)
from video_bundle_agent.media.visual_recall import create_visual_recall_slides
from video_bundle_agent.tools.process import CommandError, run_command

XHS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

NOTE_ID_RE = re.compile(
    r"(?:/explore/|/discovery/item/|/user/profile/[a-zA-Z0-9_-]+/)([a-zA-Z0-9]+)"
)
INITIAL_STATE_RE = re.compile(r"window\.__INITIAL_STATE__=({.*?})</script>", re.DOTALL)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _camel_to_snake_key(key: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()


def _snake_case_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            _camel_to_snake_key(str(key)): _snake_case_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_snake_case_json(item) for item in value]
    return value


def _deep_get(data: Any, *paths: str, default: Any = None) -> Any:
    for path in paths:
        current = data
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                if index >= len(current):
                    break
                current = current[index]
            else:
                break
        else:
            return current
    return default


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip().replace(",", "")
    if text.endswith("+"):
        text = text[:-1]
    try:
        return int(float(text))
    except ValueError:
        return None


def _iso_from_ms(value: Any) -> str:
    timestamp = _coerce_int(value)
    if not timestamp:
        return ""
    if timestamp > 10_000_000_000:
        timestamp = timestamp // 1000
    return datetime.fromtimestamp(timestamp, UTC).isoformat()


def _extract_note_id_from_url(url: str) -> str:
    match = NOTE_ID_RE.search(url)
    if match:
        return match.group(1)
    redirect_target = _redirect_path_from_login_url(url)
    if redirect_target:
        return _extract_note_id_from_url(redirect_target)
    raise ValueError(f"Could not resolve a Xiaohongshu note id from URL: {url}")


def _redirect_path_from_login_url(url: str) -> str | None:
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    if parsed.path.rstrip("/") != "/login":
        return None
    redirect_values = parse_qs(parsed.query).get("redirectPath") or []
    return redirect_values[0] if redirect_values else None


def _load_cookie_string(cookies: Path | None) -> str:
    if cookies is None:
        return ""
    values: list[str] = []
    for raw_line in cookies.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("# Netscape") or line.startswith("# Generated"):
            continue
        if line.startswith("#HttpOnly_"):
            line = line.removeprefix("#HttpOnly_")
        parts = line.split("\t")
        if len(parts) >= 7:
            domain, _subdomains, _path, _secure, _expires, name, value = parts[:7]
            normalized = domain.lstrip(".").lower()
            if normalized == "xiaohongshu.com" or normalized.endswith(".xiaohongshu.com"):
                values.append(f"{name}={value}")
            continue
        if "=" in line:
            values.append(line.rstrip(";"))
    return "; ".join(values)


def _cookie_field_presence(cookie_string: str) -> dict[str, bool]:
    names: set[str] = set()
    for item in cookie_string.split(";"):
        if "=" not in item:
            continue
        names.add(item.split("=", 1)[0].strip())
    return {
        "a1": "a1" in names,
        "web_session": "web_session" in names,
        "webId": "webId" in names,
    }


def _resolve_source_url(source_url: str, cookie_string: str) -> str:
    host = urlparse(source_url if source_url.startswith("http") else f"https://{source_url}").netloc
    if "xhslink.com" not in host.lower():
        return source_url
    headers = {"User-Agent": XHS_USER_AGENT, "Referer": "https://www.xiaohongshu.com/"}
    if cookie_string:
        headers["Cookie"] = cookie_string
    with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as client:
        response = client.get(source_url)
        response.raise_for_status()
        resolved_url = str(response.url)
        return _redirect_path_from_login_url(resolved_url) or resolved_url


def _fetch_note_html(url: str, cookie_string: str) -> str:
    headers = {"User-Agent": XHS_USER_AGENT, "Referer": "https://www.xiaohongshu.com/"}
    if cookie_string:
        headers["Cookie"] = cookie_string
    with httpx.Client(follow_redirects=True, timeout=30, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content.decode("utf-8", errors="replace")


def _note_from_initial_state(html: str, note_id: str) -> dict[str, Any]:
    match = INITIAL_STATE_RE.search(html)
    if not match:
        raise ValueError("Xiaohongshu initial state was not found in the note HTML.")
    payload = re.sub(
        r"(?P<prefix>[:\[,]\s*)undefined(?P<suffix>\s*[,\]}])",
        r"\g<prefix>null\g<suffix>",
        match.group(1),
    )
    state = _snake_case_json(json.loads(payload))
    note = _deep_get(state, f"note.note_detail_map.{note_id}.note")
    if not isinstance(note, dict):
        raise ValueError(f"Note {note_id} was not present in Xiaohongshu initial state.")
    return note


def _fetch_note_data(
    *,
    source_url: str,
    cookie_string: str,
) -> tuple[str, str, str, dict[str, Any], str]:
    resolved_url = _resolve_source_url(source_url, cookie_string)
    note_id = _extract_note_id_from_url(resolved_url)
    html = _fetch_note_html(resolved_url, cookie_string)
    try:
        note = _note_from_initial_state(html, note_id)
    except Exception:
        client = XhsClient(cookie=cookie_string or None, user_agent=XHS_USER_AGENT)
        note = client.get_note_by_id_from_html(note_id)
        note = _snake_case_json(note)
    return resolved_url, note_id, html, note, "xhs_html_initial_state"


def _normalize_tags(note: dict[str, Any]) -> list[str]:
    tags = _deep_get(note, "tag_list", default=[]) or []
    if isinstance(tags, str):
        return [item.strip() for item in tags.split(",") if item.strip()]
    items: list[str] = []
    for tag in tags:
        name = _deep_get(tag, "name")
        if name:
            items.append(str(name))
    return items


def normalize_metadata(
    *,
    source: SourceInfo,
    note: dict[str, Any],
    extractor: str,
) -> dict[str, Any]:
    interact = _deep_get(note, "interact_info", default={}) or {}
    user = _deep_get(note, "user", default={}) or {}
    note_type = str(_deep_get(note, "type", default="") or "")
    uploader = _deep_get(user, "nickname", "nick_name", default="") or _deep_get(
        note,
        "nickname",
        default="",
    )
    uploader_id = _deep_get(user, "user_id", default="") or _deep_get(
        note,
        "user_id",
        default="",
    )
    return {
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "source_url": source.source_url,
            "resolved_url": source.resolved_url,
        },
        "fetched_at": _utc_now(),
        "title": _deep_get(note, "title", default="") or "",
        "description": _deep_get(note, "desc", default="") or "",
        "duration": _coerce_int(_deep_get(note, "video.capa.duration")),
        "published_at": _iso_from_ms(_deep_get(note, "time")),
        "updated_at": _iso_from_ms(_deep_get(note, "last_update_time")),
        "uploader": uploader or "",
        "uploader_id": str(uploader_id or ""),
        "channel": "",
        "channel_id": "",
        "view_count": None,
        "like_count": _coerce_int(_deep_get(interact, "liked_count"))
        or _coerce_int(_deep_get(note, "liked_count")),
        "comment_count": _coerce_int(_deep_get(interact, "comment_count"))
        or _coerce_int(_deep_get(note, "comment_count")),
        "collect_count": _coerce_int(_deep_get(interact, "collected_count"))
        or _coerce_int(_deep_get(note, "collected_count")),
        "share_count": _coerce_int(_deep_get(interact, "share_count"))
        or _coerce_int(_deep_get(note, "share_count")),
        "thumbnail": _first_image_url(note) or "",
        "tags": _normalize_tags(note),
        "categories": [note_type] if note_type else [],
        "availability": None,
        "extractor": extractor,
        "note_type": note_type,
    }


def _decode_url(url: str) -> str:
    if not url:
        return ""
    return bytes(url, "utf-8").decode("unicode_escape")


def _image_token(url: str) -> str:
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) >= 2:
        return "/".join(path_parts[1:]).split("!")[0]
    return parsed.path.strip("/").split("!")[0]


def _image_url_from_item(item: dict[str, Any]) -> str:
    for path in ("url_default", "url", "url_pre", "url_size_large"):
        value = _deep_get(item, path)
        if value:
            return _decode_url(str(value))
    trace_id = _deep_get(item, "trace_id")
    if trace_id:
        return f"https://sns-img-bd.xhscdn.com/{trace_id}"
    return ""


def _first_image_url(note: dict[str, Any]) -> str:
    images = _deep_get(note, "image_list", default=[]) or []
    if isinstance(images, str):
        return images.split(",")[0].strip()
    for item in images:
        if isinstance(item, dict) and (url := _image_url_from_item(item)):
            return url
    return ""


def _image_urls(note: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    image_list = _deep_get(note, "image_list", default=[]) or []
    if isinstance(image_list, str):
        return [item.strip() for item in image_list.split(",") if item.strip()]
    for item in image_list:
        if not isinstance(item, dict):
            continue
        url = _image_url_from_item(item)
        if not url:
            continue
        token = _image_token(url)
        urls.append(f"https://ci.xiaohongshu.com/{token}?imageView2/format/png" if token else url)
    return urls


def _stream_url(item: dict[str, Any]) -> str:
    for path in ("master_url", "backup_urls.0", "url"):
        value = _deep_get(item, path)
        if value:
            return _decode_url(str(value))
    return ""


def _video_urls(note: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    video_url = _deep_get(note, "video_url")
    if video_url:
        urls.append(str(video_url))
    origin_key = _deep_get(note, "video.consumer.origin_video_key")
    if origin_key:
        urls.append(f"https://sns-video-bd.xhscdn.com/{origin_key}")
    streams = []
    for codec in ("h264", "h265", "h266"):
        items = _deep_get(note, f"video.media.stream.{codec}", default=[]) or []
        streams.extend(item for item in items if isinstance(item, dict))
    streams.sort(
        key=lambda item: (
            _coerce_int(_deep_get(item, "width")) or 0,
            _coerce_int(_deep_get(item, "height")) or 0,
            _coerce_int(_deep_get(item, "video_bitrate")) or 0,
        ),
        reverse=True,
    )
    for item in streams:
        if url := _stream_url(item):
            urls.append(url)
    deduped: list[str] = []
    for url in urls:
        if url and url not in deduped:
            deduped.append(url)
    return deduped


def _media_payload(
    *,
    source: SourceInfo,
    note: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "source": source.model_dump(mode="json"),
        "fetched_at": _utc_now(),
        "note_type": _deep_get(note, "type", default="") or "",
        "video_urls": _video_urls(note),
        "image_urls": _image_urls(note),
    }


def _extension_from_response(url: str, response: httpx.Response, fallback: str) -> str:
    content_type = (response.headers.get("content-type") or "").split(";")[0].strip()
    if content_type:
        guessed = mimetypes.guess_extension(content_type)
        if guessed:
            return guessed.lstrip(".")
    suffix = Path(urlparse(url).path).suffix.lstrip(".")
    return suffix or fallback


def _download_file(
    *,
    url: str,
    output_path_without_suffix: Path,
    cookie_string: str,
    fallback_suffix: str,
) -> Path:
    headers = {"User-Agent": XHS_USER_AGENT, "Referer": "https://www.xiaohongshu.com/"}
    if cookie_string:
        headers["Cookie"] = cookie_string
    output_path_without_suffix.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=120, headers=headers) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            suffix = _extension_from_response(url, response, fallback_suffix)
            output_path = output_path_without_suffix.with_suffix(f".{suffix}")
            with output_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    if chunk:
                        handle.write(chunk)
    return output_path


def _download_media_files(
    *,
    output_dir: Path,
    source_id: str,
    media: dict[str, Any],
    cookie_string: str,
) -> tuple[Path | None, list[Path], list[dict[str, Any]]]:
    raw_media_dir = output_dir / "raw" / "media"
    working_video: Path | None = None
    downloaded: list[Path] = []
    warnings: list[dict[str, Any]] = []
    video_urls = media.get("video_urls") or []
    if video_urls:
        try:
            working_video = _download_file(
                url=str(video_urls[0]),
                output_path_without_suffix=raw_media_dir / f"{source_id}.xhs-video",
                cookie_string=cookie_string,
                fallback_suffix="mp4",
            )
            downloaded.append(working_video)
        except Exception as error:  # noqa: BLE001
            warnings.append(
                {
                    "code": "VIDEO_FILE_UNAVAILABLE",
                    "severity": "warning",
                    "stage": "media_download",
                    "message": str(error),
                    "details": {
                        "exception": type(error).__name__,
                        "media_type": "video",
                        "url": str(video_urls[0]),
                    },
                }
            )
    for index, image_url in enumerate(media.get("image_urls") or [], start=1):
        try:
            downloaded.append(
                _download_file(
                    url=str(image_url),
                    output_path_without_suffix=raw_media_dir / f"{source_id}.image-{index:02d}",
                    cookie_string=cookie_string,
                    fallback_suffix="png",
                )
            )
        except Exception as error:  # noqa: BLE001
            warnings.append(
                {
                    "code": "MEDIA_DOWNLOAD_FAILED",
                    "severity": "warning",
                    "stage": "media_download",
                    "message": str(error),
                    "details": {
                        "exception": type(error).__name__,
                        "media_type": "image",
                        "url": str(image_url),
                    },
                }
            )
    return working_video, downloaded, warnings


def _normalize_comment(raw: dict[str, Any], *, source_label: str = "xhs") -> dict[str, Any]:
    user = _deep_get(raw, "user_info", default={}) or {}
    text = _deep_get(raw, "content", "text", default="") or ""
    like_count = _coerce_int(_deep_get(raw, "like_count", "liked_count")) or 0
    parent_id = _deep_get(raw, "target_comment.id", "parent_comment_id")
    if parent_id in {None, "", 0, "0"}:
        parent_id = None
    author_name = _deep_get(user, "nickname", "nick_name", default="") or _deep_get(
        raw,
        "nickname",
        default="",
    )
    author_id = _deep_get(user, "user_id", default="") or _deep_get(raw, "user_id", default="")
    return {
        "id": str(_deep_get(raw, "id", "comment_id", default="") or ""),
        "parent_id": str(parent_id) if parent_id is not None else None,
        "author_name": author_name or "",
        "author_id": str(author_id or ""),
        "text": text,
        "like_count": like_count,
        "reply_count": _coerce_int(_deep_get(raw, "sub_comment_count")) or 0,
        "published_at": _iso_from_ms(_deep_get(raw, "create_time", "time")),
        "updated_at": "",
        "is_top_level": True,
        "source": source_label,
    }


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _comment_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    question_terms = ("?", "？", "怎么", "如何", "why", "how")
    critical_terms = ("不行", "问题", "错误", "不好", "fake", "wrong", "bad", "problem")
    supportive_terms = ("谢谢", "有用", "学到", "赞", "支持", "great", "thanks", "useful")
    return {
        "top_liked": sorted(items, key=lambda item: item["like_count"], reverse=True)[:20],
        "top_replied": sorted(items, key=lambda item: item["reply_count"], reverse=True)[:20],
        "top_terms": [],
        "question_comments": [
            item for item in items if _contains_any(item["text"], question_terms)
        ][:20],
        "critical_comments": [
            item for item in items if _contains_any(item["text"], critical_terms)
        ][:20],
        "supportive_comments": [
            item for item in items if _contains_any(item["text"], supportive_terms)
        ][:20],
    }


def _mediacrawler_path() -> Path:
    return Path(os.environ.get("XHS_MEDIACRAWLER_PATH", r"D:\W\Codex\external\MediaCrawler"))


def _mediacrawler_raw_dir(output_dir: Path) -> Path:
    return (output_dir / "raw" / "xiaohongshu" / "mediacrawler").resolve()


def _mediacrawler_jsonl_files(raw_dir: Path, item_type: str) -> list[Path]:
    return sorted(
        (raw_dir / "xhs" / "jsonl").glob(f"detail_{item_type}_*.jsonl"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def _load_mediacrawler_jsonl_items(raw_dir: Path, item_type: str) -> list[dict[str, Any]]:
    files = _mediacrawler_jsonl_files(raw_dir, item_type)
    if not files:
        return []
    items: list[dict[str, Any]] = []
    for line in files[0].read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            items.append(payload)
    return items


def _run_mediacrawler_detail(
    *,
    note_url: str,
    output_dir: Path,
    max_comments: int,
) -> Path:
    mediacrawler_path = _mediacrawler_path()
    main_path = mediacrawler_path / "main.py"
    if not main_path.exists():
        raise RuntimeError(f"MediaCrawler main.py was not found: {main_path}")

    raw_dir = _mediacrawler_raw_dir(output_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    comments_requested = max_comments > 0
    if _mediacrawler_jsonl_files(raw_dir, "contents") and (
        not comments_requested or _mediacrawler_jsonl_files(raw_dir, "comments")
    ):
        return raw_dir

    default_uv = Path.home() / "AppData" / "Roaming" / "Python" / "Python312" / "Scripts" / "uv.exe"
    uv_exe = os.environ.get("UV_EXE") or (str(default_uv) if default_uv.exists() else "uv")
    runner_path = Path(__file__).resolve().parents[2] / "tools" / "mediacrawler_xhs_detail.py"
    completed = run_command(
        [
            uv_exe,
            "run",
            "python",
            str(runner_path),
            raw_dir,
            note_url,
            str(max_comments),
        ],
        cwd=mediacrawler_path,
        timeout_seconds=180,
    )
    run_path = raw_dir / "mediacrawler.run.json"
    run_path.write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "runner": str(runner_path),
                "mediacrawler_path": str(mediacrawler_path),
                "note_url": note_url,
                "max_comments": max_comments,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return raw_dir


def _fetch_mediacrawler_note_payload(
    *,
    note_url: str,
    output_dir: Path,
    max_comments: int,
) -> dict[str, Any]:
    raw_dir = _run_mediacrawler_detail(
        note_url=note_url,
        output_dir=output_dir,
        max_comments=max_comments,
    )
    items = _load_mediacrawler_jsonl_items(raw_dir, "contents")
    if not items:
        raise RuntimeError("MediaCrawler did not write detail_contents jsonl output.")
    return _snake_case_json(items[0])


def _fetch_mediacrawler_comments_payload(
    *,
    source: SourceInfo,
    output_dir: Path,
    max_comments: int,
) -> dict[str, Any]:
    if max_comments <= 0:
        return {
            "source": {
                "platform": source.platform,
                "source_id": source.source_id,
                "url": source.source_url,
            },
            "fetched_at": _utc_now(),
            "count_fetched": 0,
            "total_reported": None,
            "selection": {
                "sort": "like_count_desc",
                "limit": max_comments,
                "candidate_source": "mediacrawler_detail_jsonl",
            },
            "items": [],
            "stats": _comment_stats([]),
        }

    note_url = source.resolved_url or source.source_url
    raw_dir = _run_mediacrawler_detail(
        note_url=note_url,
        output_dir=output_dir,
        max_comments=max_comments,
    )
    comments_files = _mediacrawler_jsonl_files(raw_dir, "comments")
    if not comments_files:
        raise RuntimeError(
            "MediaCrawler did not write detail_comments jsonl output. "
            "See raw/xiaohongshu/mediacrawler/mediacrawler.run.json for process output."
        )
    comments_path = comments_files[0]
    raw_comments = _load_mediacrawler_jsonl_items(raw_dir, "comments")
    comments = [
        _normalize_comment(_snake_case_json(item), source_label="mediacrawler")
        for item in raw_comments
    ]
    items = sorted(comments, key=lambda item: item["like_count"], reverse=True)[:max_comments]
    rel_comments_path = comments_path.relative_to(raw_dir).as_posix()
    return {
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "url": source.source_url,
        },
        "fetched_at": _utc_now(),
        "count_fetched": len(items),
        "total_reported": None,
        "selection": {
            "sort": "like_count_desc",
            "limit": max_comments,
            "candidate_source": "mediacrawler_detail_jsonl",
            "raw_run_path": "raw/xiaohongshu/mediacrawler/mediacrawler.run.json",
            "raw_comments_path": f"raw/xiaohongshu/mediacrawler/{rel_comments_path}",
        },
        "items": items,
        "stats": _comment_stats(items),
    }


def _build_audience_feedback(
    *,
    metadata: dict[str, Any] | None,
    comments: dict[str, Any] | None,
    source: SourceInfo,
) -> dict[str, Any]:
    comment_stats = comments.get("stats", {}) if comments else {}
    return {
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "url": source.source_url,
        },
        "fetched_at": _utc_now(),
        "has_comments": comments is not None,
        "count_fetched": comments.get("count_fetched", 0) if comments else 0,
        "signals": {
            "like_count": metadata.get("like_count") if metadata else None,
            "comment_count": metadata.get("comment_count") if metadata else None,
            "collect_count": metadata.get("collect_count") if metadata else None,
            "share_count": metadata.get("share_count") if metadata else None,
        },
        "stats": {
            "top_liked": comment_stats.get("top_liked", []),
            "top_replied": comment_stats.get("top_replied", []),
            "top_terms": comment_stats.get("top_terms", []),
            "question_comments": comment_stats.get("question_comments", []),
            "critical_comments": comment_stats.get("critical_comments", []),
            "supportive_comments": comment_stats.get("supportive_comments", []),
        },
    }


def _write_transcript_artifacts(
    *,
    output_dir: Path,
    artifacts: BundleArtifacts,
    source: SourceInfo,
    segments: list[dict[str, Any]],
    language: str,
    transcript_source: str,
    model_path: Path | None = None,
    language_detection: dict[str, Any] | None = None,
) -> None:
    transcript_payload = build_transcript_payload(
        source=source.model_dump(mode="json"),
        segments=segments,
        language=language,
        transcript_source=transcript_source,
        model_path=model_path,
        language_detection=language_detection,
    )
    write_json(output_dir / "transcript.segments.json", transcript_payload)
    write_text(
        output_dir / "transcript.txt",
        "\n".join(segment["text"] for segment in segments) + "\n",
    )
    artifacts.add("transcript_path", "transcript", "transcript.segments.json")
    artifacts.add("transcript_text_path", "transcript_text", "transcript.txt")


def _add_transcription_info_artifacts(
    *,
    output_dir: Path,
    artifacts: BundleArtifacts,
    transcription_info: dict[str, Any],
) -> None:
    raw_json_path = transcription_info.get("raw_json_path")
    if isinstance(raw_json_path, Path):
        artifacts.add(
            "raw_transcription_json_path",
            "raw_transcription",
            raw_json_path.relative_to(output_dir).as_posix(),
        )
    language_detection = transcription_info.get("language_detection")
    if isinstance(language_detection, dict):
        sample_path = language_detection.get("sample_path")
        if isinstance(sample_path, Path):
            artifacts.add(
                "language_probe_audio_path",
                "raw_transcription",
                sample_path.relative_to(output_dir).as_posix(),
            )
        raw_output_path = language_detection.get("raw_output_path")
        if isinstance(raw_output_path, Path):
            artifacts.add(
                "language_probe_output_path",
                "raw_transcription",
                raw_output_path.relative_to(output_dir).as_posix(),
            )


def _transcribe_working_video(
    *,
    source: SourceInfo,
    output_dir: Path,
    artifacts: BundleArtifacts,
    working_video: Path,
) -> list[dict[str, Any]]:
    raw_transcription_dir = output_dir / "raw" / "transcription"
    wav_path = extract_audio_wav(
        working_video,
        raw_transcription_dir / f"{working_video.stem}.16k.wav",
    )
    artifacts.add(
        "transcription_audio_path",
        "raw_audio",
        wav_path.relative_to(output_dir).as_posix(),
    )
    transcription_info, segments = transcribe_audio_for_language(
        wav_path,
        raw_transcription_dir,
        language="zh",
    )
    _add_transcription_info_artifacts(
        output_dir=output_dir,
        artifacts=artifacts,
        transcription_info=transcription_info,
    )
    if segments:
        model_path = transcription_info.get("model_path")
        model_path = model_path if isinstance(model_path, Path) else None
        _write_transcript_artifacts(
            output_dir=output_dir,
            artifacts=artifacts,
            source=source,
            segments=segments,
            language=str(transcription_info.get("language") or "auto"),
            transcript_source=str(
                transcription_info.get("transcript_source")
                or transcription_info.get("engine")
                or "local_transcription"
            ),
            model_path=model_path,
            language_detection=transcription_info.get("language_detection")
            if isinstance(transcription_info.get("language_detection"), dict)
            else None,
        )
    return segments


def _diagnose_failure(
    diagnostics: DiagnosticLog,
    *,
    code: str,
    severity: str,
    stage: str,
    error: Exception,
) -> None:
    details: dict[str, Any] = {"exception": type(error).__name__}
    if isinstance(error, CommandError):
        details.update(
            {
                "returncode": error.returncode,
                "stderr_tail": error.stderr[-4000:],
                "stdout_tail": error.stdout[-1000:],
            }
        )
    diagnostics.add(
        code=code,
        severity=severity,  # type: ignore[arg-type]
        stage=stage,
        message=str(error),
        details=details,
    )


def _diagnose_xhs_comment_failure(
    diagnostics: DiagnosticLog,
    error: Exception,
) -> None:
    details: dict[str, Any] = {"exception": type(error).__name__}
    code = "COMMENTS_UNAVAILABLE"
    message = str(error)
    lower = message.lower()
    xhs_code_match = re.search(r"(?:-100|300011|300031)", message)
    if xhs_code_match:
        details["xhs_code"] = int(xhs_code_match.group(0))

    if (
        "selfinfo_ok=false" in lower
        or "login" in lower
        or "登录" in message
        or "-100" in message
    ):
        code = "COOKIE_REQUIRED"
        message = (
            "MediaCrawler could not fetch Xiaohongshu comments because login state "
            "is missing or expired."
        )
    elif (
        "captcha" in lower
        or "verify" in lower
        or "300011" in message
        or "300031" in message
        or "验证" in message
        or "账号存在异常" in message
    ):
        code = "PERMISSION_REQUIRED"
        message = "Xiaohongshu required interactive verification or reported account/session risk."

    diagnostics.add(
        code=code,
        severity="warning",
        stage="comments",
        message=message,
        details=details,
    )


def analyze_xiaohongshu(
    source_url: str,
    output_dir: Path,
    *,
    fetch_comments: bool = False,
    max_comments: int = 100,
    visual_recall: str = "medium",
    visual_strategy: str = "auto",
    max_screenshots: int = 0,
    force_transcription: bool = False,
    cookies: Path | None = None,
) -> dict[str, Any]:
    diagnostics = DiagnosticLog()
    artifacts = BundleArtifacts()
    capabilities = Capabilities(has_danmaku=False)
    cookie_string = _load_cookie_string(cookies)
    if cookies and not cookie_string:
        diagnostics.add(
            code="COOKIE_REQUIRED",
            severity="warning",
            stage="authentication",
            message=(
                "The provided Xiaohongshu cookies file did not contain "
                "xiaohongshu.com cookies."
            ),
            details={"cookies_path": str(cookies)},
        )
    if cookie_string:
        fields = _cookie_field_presence(cookie_string)
        if not all(fields.values()):
            diagnostics.add(
                code="COOKIE_REQUIRED",
                severity="warning",
                stage="authentication",
                message=(
                    "Xiaohongshu cookies are present, but some provider requests usually require "
                    "a1, web_session, and webId."
                ),
                details={"cookie_fields": fields},
            )

    source = SourceInfo(platform="xiaohongshu", source_url=source_url)
    metadata: dict[str, Any] | None = None
    comments_payload: dict[str, Any] | None = None
    transcript_segments: list[dict[str, Any]] = []
    working_video: Path | None = None

    try:
        try:
            resolved_url, note_id, html, note, extractor = _fetch_note_data(
                source_url=source_url,
                cookie_string=cookie_string,
            )
        except Exception as html_error:  # noqa: BLE001
            resolved_url = _resolve_source_url(source_url, cookie_string)
            note_id = _extract_note_id_from_url(resolved_url)
            fallback_source = SourceInfo(
                platform="xiaohongshu",
                source_url=source_url,
                resolved_url=resolved_url,
                source_id=note_id,
            )
            note = _fetch_mediacrawler_note_payload(
                note_url=resolved_url,
                output_dir=output_dir,
                max_comments=max_comments if fetch_comments else 0,
            )
            html = ""
            extractor = "mediacrawler_detail_jsonl"
            source = fallback_source
            diagnostics.add(
                code="METADATA_HTML_UNAVAILABLE",
                severity="warning",
                stage="metadata",
                message=(
                    "Xiaohongshu note HTML did not expose note data; "
                    "MediaCrawler detail output was used."
                ),
                details={"html_error": repr(html_error)},
            )
        source = SourceInfo(
            platform="xiaohongshu",
            source_url=source_url,
            resolved_url=resolved_url,
            source_id=note_id,
        )
        raw_dir = output_dir / "raw" / "xiaohongshu"
        raw_dir.mkdir(parents=True, exist_ok=True)
        write_text(raw_dir / "note.html", html)
        write_json(raw_dir / "note.raw.json", note)
        artifacts.add("raw_xiaohongshu_html_path", "raw_provider", "raw/xiaohongshu/note.html")
        artifacts.add(
            "raw_xiaohongshu_note_path",
            "raw_provider",
            "raw/xiaohongshu/note.raw.json",
        )
        metadata = normalize_metadata(source=source, note=note, extractor=extractor)
        write_json(output_dir / "metadata.json", metadata)
        artifacts.add("metadata_path", "metadata", "metadata.json")
        capabilities.has_metadata = True

        media_payload = _media_payload(source=source, note=note)
        write_json(output_dir / "media.json", media_payload)
        artifacts.add("media_path", "media", "media.json")
        try:
            working_video, media_paths, media_warnings = _download_media_files(
                output_dir=output_dir,
                source_id=source.source_id or "xiaohongshu-note",
                media=media_payload,
                cookie_string=cookie_string,
            )
            for warning in media_warnings:
                diagnostics.add(
                    code=str(warning["code"]),
                    severity=warning["severity"],  # type: ignore[arg-type]
                    stage=str(warning["stage"]),
                    message=str(warning["message"]),
                    details=warning.get("details") or {},
                )
            for index, media_path in enumerate(media_paths, start=1):
                kind = "raw_media"
                key = (
                    "working_video_path"
                    if media_path == working_video
                    else f"xhs_media_{index:04d}"
                )
                artifacts.add(key, kind, media_path.relative_to(output_dir).as_posix())
        except Exception as error:  # noqa: BLE001
            _diagnose_failure(
                diagnostics,
                code="VIDEO_FILE_UNAVAILABLE",
                severity="warning",
                stage="media_download",
                error=error,
            )
    except Exception as error:  # noqa: BLE001
        _diagnose_failure(
            diagnostics,
            code="METADATA_UNAVAILABLE",
            severity="error",
            stage="metadata",
            error=error,
        )

    if fetch_comments and capabilities.has_metadata:
        try:
            comments_payload = _fetch_mediacrawler_comments_payload(
                source=source,
                output_dir=output_dir,
                max_comments=max_comments,
            )
            write_json(output_dir / "comments.json", comments_payload)
            artifacts.add("comments_path", "comments", "comments.json")
            capabilities.has_comments = bool(comments_payload["items"])
        except Exception as error:  # noqa: BLE001
            diagnostics.add(
                code="COMMENTS_UNAVAILABLE",
                severity="warning",
                stage="comments",
                message="MediaCrawler did not produce Xiaohongshu comments.",
                details={"error": repr(error)},
            )
            _diagnose_xhs_comment_failure(diagnostics, error)

    if working_video is not None and (force_transcription or not transcript_segments):
        try:
            transcript_segments = _transcribe_working_video(
                source=source,
                output_dir=output_dir,
                artifacts=artifacts,
                working_video=working_video,
            )
            capabilities.has_transcript = bool(transcript_segments)
            if not transcript_segments:
                diagnostics.add(
                    code="TRANSCRIPTION_UNAVAILABLE",
                    severity="warning",
                    stage="audio_transcription",
                    message="Local audio transcription did not produce usable transcript segments.",
                )
        except Exception as error:  # noqa: BLE001
            _diagnose_failure(
                diagnostics,
                code="TRANSCRIPTION_UNAVAILABLE",
                severity="warning",
                stage="audio_transcription",
                error=error,
            )
    elif capabilities.has_metadata:
        diagnostics.add(
            code="TRANSCRIPT_UNAVAILABLE",
            severity="warning",
            stage="transcript",
            message="No Xiaohongshu video file was available for audio transcription.",
        )

    if working_video is not None and visual_recall != "none":
        try:
            slides_payload, screenshot_paths, visual_warnings = create_visual_recall_slides(
                source=source,
                source_url=source.source_url,
                video_path=working_video,
                output_dir=output_dir,
                visual_recall=visual_recall,
                visual_strategy=visual_strategy,
                max_screenshots=max_screenshots,
                transcript_segments=transcript_segments,
            )
            for warning in visual_warnings:
                diagnostics.add(
                    code=str(warning["code"]),
                    severity=warning["severity"],  # type: ignore[arg-type]
                    stage=str(warning["stage"]),
                    message=str(warning["message"]),
                    details=warning.get("details") or {},
                )
            write_json(output_dir / "slides.json", slides_payload)
            artifacts.add("slides_path", "slides", "slides.json")
            for index, screenshot_path in enumerate(screenshot_paths, start=1):
                artifacts.add(
                    f"screenshot_{index:04d}",
                    "screenshot",
                    screenshot_path.relative_to(output_dir).as_posix(),
                )
            capabilities.has_slides = bool(screenshot_paths)
        except FileNotFoundError as error:
            message = str(error).lower()
            if "ffmpeg" in message:
                code = "FFMPEG_NOT_FOUND"
            elif "ffprobe" in message:
                code = "FFPROBE_FAILED"
            else:
                code = "FRAME_EXTRACTION_FAILED"
            diagnostics.add(
                code=code,
                severity="error",
                stage="visual_recall",
                message=str(error),
            )
        except Exception as error:  # noqa: BLE001
            _diagnose_failure(
                diagnostics,
                code="FRAME_EXTRACTION_FAILED",
                severity="error",
                stage="visual_recall",
                error=error,
            )

    audience_feedback = _build_audience_feedback(
        metadata=metadata,
        comments=comments_payload,
        source=source,
    )
    write_json(output_dir / "audience_feedback.json", audience_feedback)
    artifacts.add("audience_feedback_path", "audience_feedback", "audience_feedback.json")
    capabilities.has_audience_feedback = True

    if diagnostics.status == "error":
        diagnostics.add(
            code="BUNDLE_INCOMPLETE",
            severity="warning",
            stage="bundle",
            message="Bundle was written with missing required provider data.",
        )

    bundle = finalize_bundle(
        output_dir=output_dir,
        source=source,
        artifacts=artifacts,
        capabilities=capabilities,
        diagnostics=diagnostics,
        command={
            "provider": "xiaohongshu",
            "comments": fetch_comments,
            "max_comments": max_comments,
            "visual_recall": visual_recall,
            "visual_strategy": visual_strategy,
            "max_screenshots": max_screenshots,
            "force_transcription": force_transcription,
            "cookies": str(cookies) if cookies else None,
            "no_llm": True,
        },
    )
    readiness = evaluate_bundle_readiness(output_dir)
    return {
        "status": diagnostics.status,
        "report_ready": readiness["report_ready"],
        "output_dir": str(output_dir),
        "bundle_path": str(output_dir / "bundle.json"),
        "diagnostics_path": str(output_dir / "diagnostics.json"),
        "readiness": readiness,
        "capabilities": bundle.capabilities.model_dump(mode="json"),
    }
