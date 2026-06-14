from __future__ import annotations

import asyncio
import re
from collections import Counter
from datetime import UTC, datetime
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Any

import httpx
from bilibili_api import Credential
from bilibili_api import comment as bilibili_comment
from bilibili_api import video as bilibili_video

from video_bundle_agent.bundle.readiness import evaluate_bundle_readiness
from video_bundle_agent.bundle.schema import Capabilities, SourceInfo
from video_bundle_agent.bundle.timings import StageTimings
from video_bundle_agent.bundle.writer import (
    BundleArtifacts,
    finalize_bundle,
    write_json,
    write_text,
)
from video_bundle_agent.diagnostics.models import DiagnosticLog
from video_bundle_agent.media.ffmpeg import extract_audio_wav, mux_video_audio
from video_bundle_agent.media.transcription import (
    build_transcript_payload,
    transcribe_audio_for_language,
)
from video_bundle_agent.media.visual_recall import create_visual_recall_slides
from video_bundle_agent.media.ytdlp import (
    YtDlpUnavailable,
    download_working_audio,
    download_working_video,
    dump_single_json,
)
from video_bundle_agent.providers.assets import attach_thumbnail_asset
from video_bundle_agent.providers.url_resolution import normalize_bilibili_url
from video_bundle_agent.tools.process import CommandError


def _iso_from_timestamp(value: Any) -> str:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, UTC).isoformat()
    return value if isinstance(value, str) else ""


def _published_at(info: dict[str, Any]) -> str:
    timestamp = info.get("timestamp") or info.get("release_timestamp")
    if isinstance(timestamp, int | float):
        return datetime.fromtimestamp(timestamp, UTC).isoformat()
    upload_date = info.get("upload_date")
    if isinstance(upload_date, str) and len(upload_date) == 8:
        return f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    return ""


def _extract_bvid(value: str) -> str:
    match = re.search(r"(BV[0-9A-Za-z]+)", value)
    return match.group(1) if match else ""


def _extract_aid(value: str) -> int | None:
    match = re.search(r"(?:av|aid=)(\d+)", value, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _video_from_source(
    *,
    source_url: str,
    source_id: str = "",
    aid: int | None = None,
    credential: Credential | None = None,
) -> Any:
    bvid = _extract_bvid(source_id) or _extract_bvid(source_url)
    if bvid:
        return bilibili_video.Video(bvid=bvid, credential=credential)
    if aid is not None:
        return bilibili_video.Video(aid=aid, credential=credential)
    parsed_aid = _extract_aid(source_url)
    if parsed_aid is not None:
        return bilibili_video.Video(aid=parsed_aid, credential=credential)
    return None


def _load_bilibili_credential(cookies: Path | None) -> Credential | None:
    if cookies is None:
        return None
    jar = MozillaCookieJar()
    jar.load(str(cookies), ignore_discard=True, ignore_expires=True)
    mapped_names = {
        "SESSDATA": "sessdata",
        "bili_jct": "bili_jct",
        "buvid3": "buvid3",
        "buvid4": "buvid4",
        "DedeUserID": "dedeuserid",
        "ac_time_value": "ac_time_value",
    }
    values: dict[str, str] = {}
    for cookie in jar:
        domain = cookie.domain.replace("#HttpOnly_", "").lstrip(".").lower()
        if domain != "bilibili.com" and not domain.endswith(".bilibili.com"):
            continue
        mapped_name = mapped_names.get(cookie.name)
        if mapped_name and cookie.value:
            values[mapped_name] = cookie.value
    if not values:
        return None
    return Credential(**values)


def normalize_metadata(info: dict[str, Any], source_url: str) -> dict[str, Any]:
    return {
        "source": {
            "platform": "bilibili",
            "source_id": info.get("id") or info.get("display_id") or "",
            "source_url": source_url,
            "resolved_url": info.get("webpage_url") or source_url,
        },
        "fetched_at": datetime.now(UTC).isoformat(),
        "title": info.get("title") or "",
        "description": info.get("description") or "",
        "duration": info.get("duration"),
        "published_at": _published_at(info),
        "uploader": info.get("uploader") or info.get("channel") or "",
        "uploader_id": info.get("uploader_id") or info.get("channel_id") or "",
        "channel": info.get("channel") or "",
        "channel_id": info.get("channel_id") or "",
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "thumbnail": info.get("thumbnail") or "",
        "tags": info.get("tags") or [],
        "categories": info.get("categories") or [],
        "extractor": info.get("extractor") or info.get("extractor_key") or "bilibili",
        "bv_id": info.get("id") or info.get("display_id") or "",
        "part": info.get("playlist_index"),
    }


def _apply_api_metadata(
    *,
    metadata: dict[str, Any],
    api_info: dict[str, Any],
    pages: list[dict[str, Any]],
    cid: int | None,
) -> None:
    stat = api_info.get("stat") or {}
    owner = api_info.get("owner") or {}
    bvid = api_info.get("bvid") or metadata["source"].get("source_id") or ""
    aid = api_info.get("aid")
    metadata["source"]["source_id"] = bvid or metadata["source"]["source_id"]
    metadata["source"]["resolved_url"] = (
        f"https://www.bilibili.com/video/{bvid}" if bvid else metadata["source"]["resolved_url"]
    )
    metadata["title"] = api_info.get("title") or metadata.get("title") or ""
    metadata["description"] = api_info.get("desc") or metadata.get("description") or ""
    metadata["duration"] = api_info.get("duration") or metadata.get("duration")
    metadata["published_at"] = _iso_from_timestamp(api_info.get("pubdate")) or metadata.get(
        "published_at"
    )
    metadata["uploader"] = owner.get("name") or metadata.get("uploader") or ""
    metadata["uploader_id"] = str(owner.get("mid") or metadata.get("uploader_id") or "")
    metadata["channel"] = metadata["uploader"]
    metadata["channel_id"] = metadata["uploader_id"]
    metadata["view_count"] = stat.get("view", metadata.get("view_count"))
    metadata["like_count"] = stat.get("like", metadata.get("like_count"))
    metadata["comment_count"] = stat.get("reply", metadata.get("comment_count"))
    metadata["thumbnail"] = api_info.get("pic") or metadata.get("thumbnail") or ""
    metadata["bv_id"] = bvid
    metadata["aid"] = aid
    metadata["cid"] = cid or api_info.get("cid")
    metadata["pages"] = pages
    metadata["owner"] = owner
    metadata["stat"] = stat


def _credential_cookies(credential: Credential | None) -> dict[str, str]:
    if credential is None:
        return {}
    mapping = {
        "SESSDATA": getattr(credential, "sessdata", None),
        "bili_jct": getattr(credential, "bili_jct", None),
        "buvid3": getattr(credential, "buvid3", None),
        "buvid4": getattr(credential, "buvid4", None),
        "DedeUserID": getattr(credential, "dedeuserid", None),
        "ac_time_value": getattr(credential, "ac_time_value", None),
    }
    return {name: value for name, value in mapping.items() if value}


def _format_chapter_time(seconds: Any) -> str:
    try:
        total_seconds = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return "00:00"
    minutes, second = divmod(total_seconds, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minute:02d}:{second:02d}"
    return f"{minute:02d}:{second:02d}"


def _chapter_seconds(value: Any) -> float | None:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _normalize_bilibili_source_chapters(
    *,
    source: SourceInfo,
    view_points: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for index, item in enumerate(view_points, start=1):
        start = _chapter_seconds(_first_present(item.get("from"), item.get("start")))
        if start is None:
            continue
        end = _chapter_seconds(_first_present(item.get("to"), item.get("end")))
        title = str(item.get("content") or item.get("title") or "").strip()
        time_value = _format_chapter_time(start)
        if end is not None and end > start:
            time_value = f"{time_value}-{_format_chapter_time(end)}"
        items.append(
            {
                "id": f"chapter_{len(items) + 1:04d}",
                "title": title or f"Chapter {index}",
                "start": start,
                "end": end,
                "time": time_value,
                "thumbnail": item.get("img_url") or item.get("imgUrl") or "",
                "source": "bilibili_view_points",
                "raw_type": item.get("type"),
            }
        )
    return {
        "schema_version": "0.1.0",
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "url": source.source_url,
        },
        "fetched_at": datetime.now(UTC).isoformat(),
        "chapter_source": "bilibili_player_v2.view_points",
        "count": len(items),
        "items": items,
    }


def _build_audience_feedback(
    *,
    metadata: dict[str, Any] | None,
    source: SourceInfo,
) -> dict[str, Any]:
    return {
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "url": source.source_url,
        },
        "fetched_at": datetime.now(UTC).isoformat(),
        "has_comments": False,
        "count_fetched": 0,
        "signals": {
            "view_count": metadata.get("view_count") if metadata else None,
            "like_count": metadata.get("like_count") if metadata else None,
            "comment_count": metadata.get("comment_count") if metadata else None,
        },
        "stats": {
            "top_liked": [],
            "top_replied": [],
            "top_terms": [],
            "question_comments": [],
            "critical_comments": [],
            "supportive_comments": [],
        },
    }


def _text_terms(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    words: Counter[str] = Counter()
    for item in items:
        text = str(item.get("text") or "").lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_'-]{2,}|[\u4e00-\u9fff]{2,8}", text):
            words[word] += 1
    return [{"term": term, "count": count} for term, count in words.most_common(20)]


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def _normalize_bilibili_reply(reply: dict[str, Any]) -> dict[str, Any]:
    member = reply.get("member") or {}
    content = reply.get("content") or {}
    root = reply.get("root")
    parent = reply.get("parent")
    parent_id = None
    if root not in (0, "0", None):
        parent_id = str(root)
    elif parent not in (0, "0", None):
        parent_id = str(parent)
    return {
        "id": str(reply.get("rpid") or reply.get("rpid_str") or ""),
        "parent_id": parent_id,
        "author_name": member.get("uname") or "",
        "author_id": str(member.get("mid") or reply.get("mid") or ""),
        "text": content.get("message") or "",
        "like_count": int(reply.get("like") or 0),
        "reply_count": int(reply.get("rcount") or reply.get("count") or 0),
        "published_at": _iso_from_timestamp(reply.get("ctime")),
        "updated_at": "",
        "is_top_level": parent_id is None,
        "source": "bilibili_api",
    }


def _normalize_bilibili_comments(
    *,
    source: SourceInfo,
    raw_replies: list[dict[str, Any]],
    total_reported: int | None,
    max_comments: int,
) -> dict[str, Any]:
    normalized_items = [_normalize_bilibili_reply(reply) for reply in raw_replies]
    items = sorted(
        normalized_items,
        key=lambda item: (item["like_count"], item["reply_count"]),
        reverse=True,
    )[:max_comments]
    top_liked = items[:10]
    top_replied = sorted(items, key=lambda item: item["reply_count"], reverse=True)[:10]
    question_comments = [
        item for item in items if "?" in item["text"] or "？" in item["text"]
    ][:20]
    critical_terms = ("错", "不对", "问题", "离谱", "差", "bad", "wrong", "problem")
    supportive_terms = ("谢谢", "赞", "支持", "好", "有用", "great", "good", "thanks")
    critical_comments = [item for item in items if _contains_any(item["text"], critical_terms)][
        :20
    ]
    supportive_comments = [
        item for item in items if _contains_any(item["text"], supportive_terms)
    ][:20]
    return {
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "url": source.source_url,
        },
        "fetched_at": datetime.now(UTC).isoformat(),
        "count_fetched": len(items),
        "total_reported": total_reported,
        "selection": {
            "sort": "like_count_desc",
            "limit": max_comments,
            "candidate_source": "bilibili_api_like_order",
        },
        "items": items,
        "stats": {
            "top_liked": top_liked,
            "top_replied": top_replied,
            "top_terms": _text_terms(items),
            "question_comments": question_comments,
            "critical_comments": critical_comments,
            "supportive_comments": supportive_comments,
        },
    }


def _normalize_danmaku_item(danmaku: Any) -> dict[str, Any]:
    return {
        "id": str(getattr(danmaku, "id_str", "") or getattr(danmaku, "id_", "")),
        "timestamp": float(getattr(danmaku, "dm_time", 0.0) or 0.0),
        "text": str(getattr(danmaku, "text", "") or ""),
        "send_time": _iso_from_timestamp(getattr(danmaku, "send_time", None)),
        "crc32_id": str(getattr(danmaku, "crc32_id", "") or ""),
        "color": str(getattr(danmaku, "color", "") or ""),
        "mode": int(getattr(danmaku, "mode", 0) or 0),
        "font_size": int(getattr(danmaku, "font_size", 0) or 0),
        "pool": int(getattr(danmaku, "pool", 0) or 0),
        "source": "bilibili_api",
    }


async def _fetch_api_video_context(
    *,
    source_url: str,
    source_id: str,
    aid: int | None,
    credential: Credential | None = None,
) -> tuple[Any, dict[str, Any], list[dict[str, Any]], int | None]:
    video = _video_from_source(
        source_url=source_url,
        source_id=source_id,
        aid=aid,
        credential=credential,
    )
    if video is None:
        raise ValueError("Could not resolve a Bilibili BV or AV id from the source.")
    info = await video.get_info()
    pages = await video.get_pages()
    cid = pages[0].get("cid") if pages else None
    if cid is None:
        cid = await video.get_cid(0)
    return video, info, pages, int(cid) if cid is not None else None


async def _fetch_api_player_v2(
    *,
    source_url: str,
    bvid: str,
    aid: int | None,
    cid: int,
    credential: Credential | None = None,
) -> dict[str, Any]:
    params: dict[str, str | int] = {"cid": cid}
    if bvid:
        params["bvid"] = bvid
    if aid is not None:
        params["aid"] = aid
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Referer": source_url,
    }
    async with httpx.AsyncClient(
        headers=headers,
        cookies=_credential_cookies(credential),
        follow_redirects=True,
        timeout=30,
    ) as client:
        response = await client.get(
            "https://api.bilibili.com/x/player/v2",
            params=params,
        )
        response.raise_for_status()
    payload = response.json()
    code = payload.get("code")
    if code not in (None, 0):
        raise ValueError(
            f"Bilibili player v2 returned code={code}: {payload.get('message') or ''}"
        )
    return payload


async def _fetch_api_comments(
    *,
    aid: int,
    max_comments: int,
    comment_sort: str,
    credential: Credential | None = None,
) -> tuple[list[dict[str, Any]], int | None]:
    if max_comments <= 0:
        return [], None
    order = (
        bilibili_comment.OrderType.LIKE
        if comment_sort in {"top", "like", "hot"}
        else bilibili_comment.OrderType.TIME
    )
    replies: list[dict[str, Any]] = []
    total_reported: int | None = None
    page_index = 1
    while len(replies) < max_comments and page_index <= 20:
        payload = await bilibili_comment.get_comments(
            aid,
            bilibili_comment.CommentResourceType.VIDEO,
            page_index=page_index,
            order=order,
            credential=credential,
        )
        page = payload.get("page") or {}
        if isinstance(page.get("count"), int):
            total_reported = page["count"]
        page_replies = [
            reply for reply in payload.get("replies") or [] if isinstance(reply, dict)
        ]
        if not page_replies:
            break
        replies.extend(page_replies)
        if len(page_replies) < int(page.get("size") or len(page_replies)):
            break
        page_index += 1
    return replies[:max_comments], total_reported


async def _fetch_api_danmakus(
    *,
    video: Any,
    cid: int,
    max_danmaku: int,
    max_segments: int = 12,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if max_danmaku <= 0:
        return [], {"max_danmaku": max_danmaku, "segments_requested": 0, "sampled": False}
    items: list[dict[str, Any]] = []
    segments_requested = 0
    for segment in range(max_segments):
        danmakus = await video.get_danmakus(
            page_index=0,
            cid=cid,
            from_seg=segment,
            to_seg=segment + 1,
        )
        segments_requested += 1
        if not danmakus:
            break
        for danmaku in danmakus:
            items.append(_normalize_danmaku_item(danmaku))
            if len(items) >= max_danmaku:
                break
        if len(items) >= max_danmaku:
            break
    return items, {
        "max_danmaku": max_danmaku,
        "max_segments": max_segments,
        "segments_requested": segments_requested,
        "sampled": len(items) >= max_danmaku or segments_requested >= max_segments,
    }


async def _fetch_api_download_url(*, video: Any, cid: int) -> dict[str, Any]:
    return await video.get_download_url(cid=cid)


def _build_danmaku_payload(
    *,
    source: SourceInfo,
    cid: int | None,
    items: list[dict[str, Any]],
    sampling: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "url": source.source_url,
        },
        "fetched_at": datetime.now(UTC).isoformat(),
        "cid": cid,
        "count_fetched": len(items),
        "total_reported": None,
        "is_sampled": bool(sampling.get("sampled")),
        "sampling": sampling,
        "items": items,
        "stats": {
            "top_terms": _text_terms(items),
        },
    }


def _stream_url(stream: dict[str, Any]) -> str:
    return str(stream.get("baseUrl") or stream.get("base_url") or "")


def _select_dash_video_stream(
    streams: list[dict[str, Any]],
    *,
    max_height: int = 1080,
) -> dict[str, Any] | None:
    candidates = [stream for stream in streams if _stream_url(stream)]
    bounded = [
        stream
        for stream in candidates
        if int(stream.get("height") or 0) <= max_height or not stream.get("height")
    ]
    candidates = bounded or candidates
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda stream: (
            int(stream.get("height") or 0),
            int(stream.get("bandwidth") or 0),
        ),
    )


def _select_dash_audio_stream(streams: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [stream for stream in streams if _stream_url(stream)]
    if not candidates:
        return None
    return max(candidates, key=lambda stream: int(stream.get("bandwidth") or 0))


def _download_url(
    *,
    url: str,
    output_path: Path,
    source_url: str,
    timeout_seconds: int = 1800,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Referer": source_url,
        "Accept": "*/*",
    }
    with httpx.stream(
        "GET",
        url,
        headers=headers,
        follow_redirects=True,
        timeout=timeout_seconds,
    ) as response:
        response.raise_for_status()
        with output_path.open("wb") as handle:
            for chunk in response.iter_bytes(1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return output_path


def _download_api_working_media(
    *,
    download_url_payload: dict[str, Any],
    output_dir: Path,
    source_id: str,
    source_url: str,
    max_height: int = 1080,
) -> tuple[Path, Path]:
    dash = download_url_payload.get("dash") or {}
    video_stream = _select_dash_video_stream(dash.get("video") or [], max_height=max_height)
    audio_stream = _select_dash_audio_stream(dash.get("audio") or [])
    if video_stream is None or audio_stream is None:
        raise FileNotFoundError("Bilibili API playurl did not provide DASH video/audio URLs.")

    safe_source_id = source_id or "bilibili-video"
    raw_video = _download_url(
        url=_stream_url(video_stream),
        output_path=output_dir / f"{safe_source_id}.video.m4s",
        source_url=source_url,
    )
    raw_audio = _download_url(
        url=_stream_url(audio_stream),
        output_path=output_dir / f"{safe_source_id}.audio.m4s",
        source_url=source_url,
    )
    merged = mux_video_audio(
        video_path=raw_video,
        audio_path=raw_audio,
        output_path=output_dir / f"{safe_source_id}.api.mp4",
    )
    return merged, raw_audio


def _select_bilibili_subtitle_file(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    ordered = sorted(paths, key=lambda path: path.name.lower())
    priorities = (
        ".zh-hans.",
        ".zh-hant.",
        ".zh.",
        ".en.",
    )
    for priority in priorities:
        for path in ordered:
            if priority in path.name.lower():
                return path
    return ordered[0]


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


def _diagnose_command_failure(
    diagnostics: DiagnosticLog,
    *,
    code: str,
    severity: str,
    stage: str,
    error: Exception,
) -> None:
    details: dict[str, Any] = {"exception": type(error).__name__}
    if isinstance(error, CommandError):
        stderr_lower = error.stderr.lower()
        if "login" in stderr_lower or "cookies" in stderr_lower:
            code = "COOKIE_REQUIRED"
        elif "rate limit" in stderr_lower or "too many requests" in stderr_lower:
            code = "RATE_LIMITED"
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


def _diagnose_transcription_failure(
    diagnostics: DiagnosticLog,
    *,
    error: Exception,
) -> None:
    code = "TRANSCRIPTION_UNAVAILABLE"
    details: dict[str, Any] = {"exception": type(error).__name__}
    if isinstance(error, FileNotFoundError):
        message = str(error).lower()
        if "whisper.cpp cli" in message:
            code = "TOOL_MISSING"
        elif "funasr" in message:
            code = "TOOL_MISSING"
        elif "model" in message:
            code = "WHISPER_MODEL_MISSING"
        elif "ffmpeg" in message:
            code = "FFMPEG_NOT_FOUND"
        elif "audio" in message:
            code = "AUDIO_UNAVAILABLE"
    elif isinstance(error, CommandError):
        details.update(
            {
                "returncode": error.returncode,
                "stderr_tail": error.stderr[-4000:],
                "stdout_tail": error.stdout[-1000:],
            }
        )
    diagnostics.add(
        code=code,
        severity="warning",
        stage="audio_transcription",
        message=str(error),
        details=details,
    )


def _transcribe_audio(
    *,
    source_url: str,
    source: SourceInfo,
    output_dir: Path,
    artifacts: BundleArtifacts,
    raw_audio_dir: Path,
    raw_transcription_dir: Path,
    cookies: Path | None,
    cookies_from_browser: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    working_audio = download_working_audio(
        source_url,
        raw_audio_dir,
        source_id=source.source_id or "bilibili-audio",
        cookies=cookies,
        cookies_from_browser=cookies_from_browser,
    )
    artifacts.add(
        "working_audio_path",
        "raw_audio",
        working_audio.relative_to(output_dir).as_posix(),
    )
    wav_path = extract_audio_wav(
        working_audio,
        raw_transcription_dir / f"{working_audio.stem}.16k.wav",
    )
    artifacts.add(
        "transcription_audio_path",
        "raw_audio",
        wav_path.relative_to(output_dir).as_posix(),
    )
    transcription_info, transcribed_segments = transcribe_audio_for_language(
        wav_path,
        raw_transcription_dir,
        language="zh",
    )
    _add_transcription_info_artifacts(
        output_dir=output_dir,
        artifacts=artifacts,
        transcription_info=transcription_info,
    )
    return transcription_info, transcribed_segments


def _transcribe_existing_audio(
    *,
    audio_path: Path,
    output_dir: Path,
    artifacts: BundleArtifacts,
    raw_transcription_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    wav_path = extract_audio_wav(
        audio_path,
        raw_transcription_dir / f"{audio_path.stem}.16k.wav",
    )
    artifacts.add(
        "transcription_audio_path",
        "raw_audio",
        wav_path.relative_to(output_dir).as_posix(),
    )
    transcription_info, transcribed_segments = transcribe_audio_for_language(
        wav_path,
        raw_transcription_dir,
        language="zh",
    )
    _add_transcription_info_artifacts(
        output_dir=output_dir,
        artifacts=artifacts,
        transcription_info=transcription_info,
    )
    return transcription_info, transcribed_segments


def analyze_bilibili(
    source_url: str,
    output_dir: Path,
    *,
    fetch_comments: bool = False,
    max_comments: int = 100,
    comment_sort: str = "top",
    max_danmaku: int = 0,
    visual_recall: str = "medium",
    visual_strategy: str = "auto",
    max_screenshots: int = 0,
    force_transcription: bool = False,
    cookies: Path | None = None,
    cookies_from_browser: str | None = None,
) -> dict[str, Any]:
    timings = StageTimings()
    diagnostics = DiagnosticLog()
    artifacts = BundleArtifacts()
    capabilities = Capabilities(has_danmaku=False)
    bilibili_credential: Credential | None = None
    if cookies is not None:
        try:
            bilibili_credential = _load_bilibili_credential(cookies)
            if bilibili_credential is None:
                diagnostics.add(
                    code="COOKIE_REQUIRED",
                    severity="warning",
                    stage="authentication",
                    message=(
                        "The provided cookies file did not contain Bilibili credential "
                        "fields needed by bilibili-api-python."
                    ),
                    details={"cookies_path": str(cookies)},
                )
        except Exception as error:  # noqa: BLE001
            diagnostics.add(
                code="COOKIE_REQUIRED",
                severity="warning",
                stage="authentication",
                message=f"Could not parse Bilibili cookies file: {error}",
                details={"exception": type(error).__name__, "cookies_path": str(cookies)},
            )
    raw_media_dir = output_dir / "raw" / "media"
    raw_audio_dir = output_dir / "raw" / "audio"
    raw_transcription_dir = output_dir / "raw" / "transcription"
    raw_api_dir = output_dir / "raw" / "bilibili_api"
    working_source_url = source_url
    try:
        with timings.stage("url_resolution"):
            resolved_input = normalize_bilibili_url(source_url)
            working_source_url = resolved_input.working_url
            if resolved_input.changed:
                diagnostics.add(
                    code="SOURCE_URL_NORMALIZED",
                    severity="info",
                    stage="url_resolution",
                    message="Bilibili source URL was normalized before provider collection.",
                    details={
                        "original_url": source_url,
                        "working_url": working_source_url,
                        "method": resolved_input.method,
                    },
                )
    except Exception as error:  # noqa: BLE001
        diagnostics.add(
            code="SOURCE_URL_RESOLUTION_FAILED",
            severity="warning",
            stage="url_resolution",
            message=f"Could not normalize Bilibili source URL: {error}",
            details={"exception": type(error).__name__, "source_url": source_url},
        )

    api_video: Any | None = None
    api_info: dict[str, Any] | None = None
    api_pages: list[dict[str, Any]] = []
    aid: int | None = None
    cid: int | None = None
    metadata: dict[str, Any] | None = None
    source = SourceInfo(platform="bilibili", source_url=source_url)
    transcript_segments: list[dict[str, Any]] = []
    api_metadata_error: Exception | None = None

    try:
        with timings.stage("metadata"):
            api_video, api_info, api_pages, cid = asyncio.run(
                _fetch_api_video_context(
                    source_url=working_source_url,
                    source_id="",
                    aid=aid,
                    credential=bilibili_credential,
                )
            )
            raw_api_dir.mkdir(parents=True, exist_ok=True)
            write_json(raw_api_dir / "video_info.json", api_info)
            write_json(raw_api_dir / "pages.json", {"items": api_pages})
            artifacts.add(
                "bilibili_api_video_info_path",
                "raw_provider",
                (raw_api_dir / "video_info.json").relative_to(output_dir).as_posix(),
            )
            artifacts.add(
                "bilibili_api_pages_path",
                "raw_provider",
                (raw_api_dir / "pages.json").relative_to(output_dir).as_posix(),
            )
            aid = api_info.get("aid") if isinstance(api_info.get("aid"), int) else aid
            metadata = normalize_metadata(
                {
                    "id": api_info.get("bvid") or "",
                    "webpage_url": f"https://www.bilibili.com/video/{api_info.get('bvid')}",
                    "title": api_info.get("title") or "",
                    "description": api_info.get("desc") or "",
                    "duration": api_info.get("duration"),
                    "timestamp": api_info.get("pubdate"),
                    "uploader": (api_info.get("owner") or {}).get("name") or "",
                    "uploader_id": str((api_info.get("owner") or {}).get("mid") or ""),
                    "view_count": (api_info.get("stat") or {}).get("view"),
                    "like_count": (api_info.get("stat") or {}).get("like"),
                    "comment_count": (api_info.get("stat") or {}).get("reply"),
                    "thumbnail": api_info.get("pic") or "",
                },
                source_url,
            )
            _apply_api_metadata(metadata=metadata, api_info=api_info, pages=api_pages, cid=cid)
            source = SourceInfo(
                platform="bilibili",
                source_url=source_url,
                resolved_url=metadata["source"]["resolved_url"],
                source_id=metadata["source"]["source_id"],
            )
        if cid is not None:
            try:
                player_v2_payload = asyncio.run(
                    _fetch_api_player_v2(
                        source_url=working_source_url,
                        bvid=str(api_info.get("bvid") or source.source_id or ""),
                        aid=aid,
                        cid=cid,
                        credential=bilibili_credential,
                    )
                )
                raw_api_dir.mkdir(parents=True, exist_ok=True)
                write_json(raw_api_dir / "player_v2.json", player_v2_payload)
                artifacts.add(
                    "bilibili_api_player_v2_path",
                    "raw_provider",
                    (raw_api_dir / "player_v2.json").relative_to(output_dir).as_posix(),
                )
                player_data = player_v2_payload.get("data") or {}
                view_points = [
                    item
                    for item in player_data.get("view_points") or []
                    if isinstance(item, dict)
                ]
                source_chapters = _normalize_bilibili_source_chapters(
                    source=source,
                    view_points=view_points,
                )
                write_json(output_dir / "source_chapters.json", source_chapters)
                artifacts.add(
                    "source_chapters_path",
                    "source_chapters",
                    "source_chapters.json",
                )
            except Exception as error:  # noqa: BLE001
                _diagnose_command_failure(
                    diagnostics,
                    code="SOURCE_CHAPTERS_UNAVAILABLE",
                    severity="warning",
                    stage="source_chapters",
                    error=error,
                )
        if metadata is not None:
            attach_thumbnail_asset(
                metadata=metadata,
                output_dir=output_dir,
                artifacts=artifacts,
                diagnostics=diagnostics,
                source_id=source.source_id or "bilibili-video",
                referer=source.resolved_url or working_source_url,
            )
        write_json(output_dir / "metadata.json", metadata)
        artifacts.add("metadata_path", "metadata", "metadata.json")
        capabilities.has_metadata = True
    except Exception as error:  # noqa: BLE001
        api_metadata_error = error

    if not capabilities.has_metadata:
        try:
            with timings.stage("metadata_fallback"):
                info = dump_single_json(
                    working_source_url,
                    write_comments=False,
                    cookies=cookies,
                    cookies_from_browser=cookies_from_browser,
                )
                metadata = normalize_metadata(info, source_url)
                aid = info.get("aid") if isinstance(info.get("aid"), int) else None
                source = SourceInfo(
                    platform="bilibili",
                    source_url=source_url,
                    resolved_url=metadata["source"]["resolved_url"],
                    source_id=metadata["source"]["source_id"],
                )
                attach_thumbnail_asset(
                    metadata=metadata,
                    output_dir=output_dir,
                    artifacts=artifacts,
                    diagnostics=diagnostics,
                    source_id=source.source_id or "bilibili-video",
                    referer=source.resolved_url or working_source_url,
                )
                write_json(output_dir / "metadata.json", metadata)
                artifacts.add("metadata_path", "metadata", "metadata.json")
                capabilities.has_metadata = True
            if api_metadata_error is not None:
                _diagnose_command_failure(
                    diagnostics,
                    code="BILIBILI_API_UNAVAILABLE",
                    severity="warning",
                    stage="bilibili_api_metadata",
                    error=api_metadata_error,
                )
        except YtDlpUnavailable as error:
            diagnostics.add(
                code="TOOL_MISSING",
                severity="error",
                stage="metadata",
                message=str(error),
            )
            if api_metadata_error is not None:
                _diagnose_command_failure(
                    diagnostics,
                    code="BILIBILI_API_UNAVAILABLE",
                    severity="error",
                    stage="bilibili_api_metadata",
                    error=api_metadata_error,
                )
        except Exception as error:  # noqa: BLE001
            _diagnose_command_failure(
                diagnostics,
                code="METADATA_UNAVAILABLE",
                severity="error",
                stage="metadata",
                error=error,
            )
            if api_metadata_error is not None:
                _diagnose_command_failure(
                    diagnostics,
                    code="BILIBILI_API_UNAVAILABLE",
                    severity="error",
                    stage="bilibili_api_metadata",
                    error=api_metadata_error,
                )

    comments_payload: dict[str, Any] | None = None
    if fetch_comments:
        if aid is None:
            diagnostics.add(
                code="COMMENTS_UNAVAILABLE",
                severity="warning",
                stage="comments",
                message="Bilibili comments require an AV id, but no aid was resolved.",
            )
        else:
            try:
                with timings.stage("comments", {"max_comments": max_comments}):
                    raw_replies, total_reported = asyncio.run(
                        _fetch_api_comments(
                            aid=aid,
                            max_comments=max_comments,
                            comment_sort=comment_sort,
                            credential=bilibili_credential,
                        )
                    )
                    comments_payload = _normalize_bilibili_comments(
                        source=source,
                        raw_replies=raw_replies,
                        total_reported=total_reported,
                        max_comments=max_comments,
                    )
                    write_json(output_dir / "comments.json", comments_payload)
                    artifacts.add("comments_path", "comments", "comments.json")
                    capabilities.has_comments = bool(comments_payload["items"])
                requested_count = min(
                    max_comments,
                    total_reported if total_reported is not None else max_comments,
                )
                if comments_payload["count_fetched"] < requested_count:
                    comment_diag_code = (
                        "COOKIE_REQUIRED"
                        if bilibili_credential is None
                        else "COMMENTS_UNAVAILABLE"
                    )
                    diagnostics.add(
                        code=comment_diag_code,
                        severity="warning",
                        stage="comments",
                        message=(
                            "Bilibili comments were only partially fetched: "
                            f"{comments_payload['count_fetched']} of requested "
                            f"{requested_count}."
                        ),
                        details={
                            "count_fetched": comments_payload["count_fetched"],
                            "requested_count": requested_count,
                            "total_reported": total_reported,
                            "has_bilibili_credential": bilibili_credential is not None,
                            "note": (
                                "Pass --cookies with a Bilibili Netscape cookies file to "
                                "enable authenticated pagination."
                            )
                            if bilibili_credential is None
                            else "Authenticated pagination still returned fewer comments.",
                        },
                    )
            except Exception as error:  # noqa: BLE001
                _diagnose_command_failure(
                    diagnostics,
                    code="COMMENTS_UNAVAILABLE",
                    severity="warning",
                    stage="comments",
                    error=error,
                )

    danmaku_payload: dict[str, Any] | None = None
    if max_danmaku > 0 and api_video is not None and cid is not None:
        try:
            with timings.stage("danmaku", {"max_danmaku": max_danmaku}):
                danmaku_items, danmaku_sampling = asyncio.run(
                    _fetch_api_danmakus(
                        video=api_video,
                        cid=cid,
                        max_danmaku=max_danmaku,
                    )
                )
                danmaku_payload = _build_danmaku_payload(
                    source=source,
                    cid=cid,
                    items=danmaku_items,
                    sampling=danmaku_sampling,
                )
                write_json(output_dir / "danmaku.json", danmaku_payload)
                artifacts.add("danmaku_path", "danmaku", "danmaku.json")
                capabilities.has_danmaku = bool(danmaku_items)
        except Exception as error:  # noqa: BLE001
            _diagnose_command_failure(
                diagnostics,
                code="DANMAKU_UNAVAILABLE",
                severity="warning",
                stage="danmaku",
                error=error,
            )
    elif max_danmaku > 0:
        diagnostics.add(
            code="DANMAKU_UNAVAILABLE",
            severity="warning",
            stage="danmaku",
            message="Bilibili danmaku requires a resolved cid.",
        )

    working_video: Path | None = None
    working_audio: Path | None = None
    if capabilities.has_metadata and api_video is not None and cid is not None:
        try:
            with timings.stage("media_download", {"method": "bilibili_api"}):
                download_url_payload = asyncio.run(
                    _fetch_api_download_url(video=api_video, cid=cid)
                )
                raw_api_dir.mkdir(parents=True, exist_ok=True)
                write_json(raw_api_dir / "download_url.json", download_url_payload)
                artifacts.add(
                    "bilibili_api_download_url_path",
                    "raw_provider",
                    (raw_api_dir / "download_url.json").relative_to(output_dir).as_posix(),
                )
                working_video, working_audio = _download_api_working_media(
                    download_url_payload=download_url_payload,
                    output_dir=raw_media_dir,
                    source_id=source.source_id or "bilibili-video",
                    source_url=working_source_url,
                )
                artifacts.add(
                    "working_video_path",
                    "raw_media",
                    working_video.relative_to(output_dir).as_posix(),
                )
                artifacts.add(
                    "working_audio_path",
                    "raw_audio",
                    working_audio.relative_to(output_dir).as_posix(),
                )
        except Exception as api_error:  # noqa: BLE001
            _diagnose_command_failure(
                diagnostics,
                code="BILIBILI_API_UNAVAILABLE",
                severity="warning",
                stage="media_download",
                error=api_error,
            )

    if working_video is None and capabilities.has_metadata:
        try:
            with timings.stage("media_download", {"method": "yt_dlp_fallback"}):
                working_video = download_working_video(
                    working_source_url,
                    raw_media_dir,
                    source_id=source.source_id or "bilibili-video",
                    max_height=1080,
                    cookies=cookies,
                    cookies_from_browser=cookies_from_browser,
                )
                artifacts.add(
                    "working_video_path",
                    "raw_media",
                    working_video.relative_to(output_dir).as_posix(),
                )
        except Exception as error:  # noqa: BLE001
            _diagnose_command_failure(
                diagnostics,
                code="VIDEO_FILE_UNAVAILABLE",
                severity="error",
                stage="media_download",
                error=error,
            )

    if working_video is not None and (force_transcription or not transcript_segments):
        try:
            with timings.stage("audio_transcription"):
                if working_audio is not None:
                    transcription_info, transcribed_segments = _transcribe_existing_audio(
                        audio_path=working_audio,
                        output_dir=output_dir,
                        artifacts=artifacts,
                        raw_transcription_dir=raw_transcription_dir,
                    )
                else:
                    transcription_info, transcribed_segments = _transcribe_audio(
                        source_url=working_source_url,
                        source=source,
                        output_dir=output_dir,
                        artifacts=artifacts,
                        raw_audio_dir=raw_audio_dir,
                        raw_transcription_dir=raw_transcription_dir,
                        cookies=cookies,
                        cookies_from_browser=cookies_from_browser,
                    )
                if transcribed_segments:
                    model_path = transcription_info.get("model_path")
                    model_path = model_path if isinstance(model_path, Path) else None
                    transcript_segments = transcribed_segments
                    _write_transcript_artifacts(
                        output_dir=output_dir,
                        artifacts=artifacts,
                        source=source,
                        segments=transcript_segments,
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
                    capabilities.has_transcript = True
                else:
                    diagnostics.add(
                        code="TRANSCRIPTION_UNAVAILABLE",
                        severity="warning",
                        stage="audio_transcription",
                        message=(
                            "Local audio transcription did not produce usable "
                            "transcript segments."
                        ),
                    )
        except Exception as error:  # noqa: BLE001
            _diagnose_transcription_failure(diagnostics, error=error)
            if not transcript_segments:
                diagnostics.add(
                    code="TRANSCRIPT_UNAVAILABLE",
                    severity="warning",
                    stage="transcript",
                    message="Bilibili transcript was unavailable and audio transcription failed.",
                )

    if working_video is not None and visual_recall != "none":
        try:
            with timings.stage(
                "visual_recall",
                {"visual_recall": visual_recall, "visual_strategy": visual_strategy},
            ):
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
            _diagnose_command_failure(
                diagnostics,
                code="FRAME_EXTRACTION_FAILED",
                severity="error",
                stage="visual_recall",
                error=error,
            )

    with timings.stage("audience_feedback"):
        audience_feedback = _build_audience_feedback(metadata=metadata, source=source)
        if comments_payload is not None:
            audience_feedback["has_comments"] = True
            audience_feedback["count_fetched"] = comments_payload["count_fetched"]
            audience_feedback["stats"] = comments_payload["stats"]
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

    timings.write(output_dir / "timings.json")
    artifacts.add("timings_path", "timings", "timings.json")

    bundle = finalize_bundle(
        output_dir=output_dir,
        source=source,
        artifacts=artifacts,
        capabilities=capabilities,
        diagnostics=diagnostics,
        command={
            "provider": "bilibili",
            "provider_stage": "bilibili_api_primary",
            "comments": fetch_comments,
            "max_comments": max_comments,
            "comment_sort": comment_sort,
            "max_danmaku": max_danmaku,
            "visual_recall": visual_recall,
            "visual_strategy": visual_strategy,
            "max_screenshots": max_screenshots,
            "force_transcription": force_transcription,
            "cookies": str(cookies) if cookies else None,
            "cookies_from_browser": cookies_from_browser,
            "no_llm": True,
        },
    )
    readiness = evaluate_bundle_readiness(output_dir)
    return {
        "status": diagnostics.status,
        "report_ready": readiness["report_ready"],
        "output_dir": str(output_dir),
        "bundle_path": str(output_dir / "bundle.json"),
        "timings_path": str(output_dir / "timings.json"),
        "diagnostics_path": str(output_dir / "diagnostics.json"),
        "readiness": readiness,
        "capabilities": bundle.capabilities.model_dump(mode="json"),
    }
