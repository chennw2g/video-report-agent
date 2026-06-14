from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from video_bundle_agent.bundle.readiness import evaluate_bundle_readiness
from video_bundle_agent.bundle.schema import Capabilities, SourceInfo
from video_bundle_agent.bundle.transcript_compare import write_transcript_comparison
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
from video_bundle_agent.media.ytdlp import (
    YtDlpUnavailable,
    download_working_audio,
    download_working_video,
    dump_single_json,
    write_subtitles,
)
from video_bundle_agent.providers.youtube.comments import normalize_comments
from video_bundle_agent.providers.youtube.transcript import parse_subtitle, select_subtitle_file
from video_bundle_agent.tools.process import CommandError


def _published_at(info: dict[str, Any]) -> str:
    timestamp = info.get("timestamp")
    if isinstance(timestamp, int | float):
        return datetime.fromtimestamp(timestamp, UTC).isoformat()
    upload_date = info.get("upload_date")
    if isinstance(upload_date, str) and len(upload_date) == 8:
        return f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    return ""


def normalize_metadata(info: dict[str, Any], source_url: str) -> dict[str, Any]:
    return {
        "source": {
            "platform": "youtube",
            "source_id": info.get("id") or "",
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
        "availability": info.get("availability"),
        "extractor": info.get("extractor") or info.get("extractor_key") or "youtube",
    }


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


def normalize_source_chapters(
    *,
    source: SourceInfo,
    chapters: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for index, chapter in enumerate(chapters, start=1):
        start = _chapter_seconds(
            _first_present(chapter.get("start_time"), chapter.get("start"))
        )
        if start is None:
            continue
        end = _chapter_seconds(_first_present(chapter.get("end_time"), chapter.get("end")))
        title = str(chapter.get("title") or "").strip()
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
                "thumbnail": chapter.get("thumbnail") or "",
                "source": "yt_dlp_chapters",
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
        "chapter_source": "yt_dlp.chapters",
        "count": len(items),
        "items": items,
    }


def build_audience_feedback(
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
        "fetched_at": datetime.now(UTC).isoformat(),
        "has_comments": comments is not None,
        "count_fetched": comments.get("count_fetched", 0) if comments else 0,
        "signals": {
            "view_count": metadata.get("view_count") if metadata else None,
            "like_count": metadata.get("like_count") if metadata else None,
            "comment_count": metadata.get("comment_count") if metadata else None,
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


def _jsonable_dict(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    result: dict[str, Any] = {}
    for key, item in value.items():
        result[key] = str(item) if isinstance(item, Path) else item
    return result


def _write_transcript_alternative_artifacts(
    *,
    output_dir: Path,
    artifacts: BundleArtifacts,
    source: SourceInfo,
    primary_transcript_path: str,
    segments: list[dict[str, Any]],
    language: str,
    transcript_source: str,
    reason: str,
    model_path: Path | None = None,
    language_detection: dict[str, Any] | None = None,
) -> None:
    suffix = "funasr" if "funasr" in transcript_source.lower() else "whisper"
    transcript_path = f"transcript.{suffix}.segments.json"
    transcript_text_path = f"transcript.{suffix}.txt"
    jsonable_language_detection = _jsonable_dict(language_detection)
    transcript_payload = build_transcript_payload(
        source=source.model_dump(mode="json"),
        segments=segments,
        language=language,
        transcript_source=transcript_source,
        model_path=model_path,
        language_detection=jsonable_language_detection,
    )
    write_json(output_dir / transcript_path, transcript_payload)
    write_text(
        output_dir / transcript_text_path,
        "\n".join(segment["text"] for segment in segments) + "\n",
    )
    alternatives_payload = {
        "schema_version": "0.1.0",
        "source": source.model_dump(mode="json"),
        "fetched_at": datetime.now(UTC).isoformat(),
        "primary_transcript_path": primary_transcript_path,
        "items": [
            {
                "transcript_source": transcript_source,
                "language": language,
                "reason": reason,
                "transcript_path": transcript_path,
                "transcript_text_path": transcript_text_path,
                "segment_count": len(segments),
                "model_path": str(model_path) if model_path else None,
                "language_detection": jsonable_language_detection,
            }
        ],
    }
    write_json(output_dir / "transcript.alternatives.json", alternatives_payload)
    artifacts.add(
        "transcript_alternatives_path",
        "transcript_alternatives",
        "transcript.alternatives.json",
    )
    artifacts.add("transcript_local_path", "transcript_alternative", transcript_path)
    artifacts.add("transcript_whisper_path", "transcript_alternative", transcript_path)
    artifacts.add(
        "transcript_local_text_path",
        "transcript_alternative_text",
        transcript_text_path,
    )
    artifacts.add(
        "transcript_whisper_text_path",
        "transcript_alternative_text",
        transcript_text_path,
    )


def _has_manual_subtitles(info: dict[str, Any]) -> bool:
    subtitles = info.get("subtitles")
    if not isinstance(subtitles, dict):
        return False
    return any(bool(tracks) for tracks in subtitles.values())


def _subtitle_transcript_source(info: dict[str, Any]) -> str:
    if _has_manual_subtitles(info):
        return "yt_dlp_manual_subtitle"
    return "yt_dlp_auto_subtitle"


def _infer_local_transcription_language(
    *,
    info: dict[str, Any],
    subtitle_language_hint: str,
) -> str:
    candidates = [
        info.get("language"),
        info.get("language_preference"),
        info.get("channel_language"),
        subtitle_language_hint,
    ]
    joined = " ".join(str(item).lower() for item in candidates if item)
    if any(token in joined for token in ("zh", "chi", "chinese", "cmn", "yue")):
        return "zh"
    if "en" in joined or "english" in joined:
        return "en"
    return "auto"


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


def _run_local_transcription(
    *,
    source_url: str,
    source: SourceInfo,
    output_dir: Path,
    artifacts: BundleArtifacts,
    raw_audio_dir: Path,
    raw_transcription_dir: Path,
    language: str,
    cookies: Path | None,
    cookies_from_browser: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    working_audio = download_working_audio(
        source_url,
        raw_audio_dir,
        source_id=source.source_id or "youtube-audio",
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
        language=language,
    )
    _add_transcription_info_artifacts(
        output_dir=output_dir,
        artifacts=artifacts,
        transcription_info=transcription_info,
    )
    return transcription_info, transcribed_segments


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
        if "not a bot" in stderr_lower or "use --cookies" in stderr_lower:
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


def analyze_youtube(
    source_url: str,
    output_dir: Path,
    *,
    fetch_comments: bool,
    max_comments: int = 100,
    comment_sort: str = "top",
    visual_recall: str = "medium",
    visual_strategy: str = "auto",
    max_screenshots: int = 0,
    force_transcription: bool = False,
    compare_auto_subtitles: bool = True,
    cookies: Path | None = None,
    cookies_from_browser: str | None = None,
) -> dict[str, Any]:
    diagnostics = DiagnosticLog()
    artifacts = BundleArtifacts()
    capabilities = Capabilities(has_danmaku=False)
    raw_dir = output_dir / "raw" / "yt_dlp"
    raw_media_dir = output_dir / "raw" / "media"
    raw_audio_dir = output_dir / "raw" / "audio"
    raw_transcription_dir = output_dir / "raw" / "transcription"

    info: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    source = SourceInfo(platform="youtube", source_url=source_url)

    try:
        info = dump_single_json(
            source_url,
            write_comments=False,
            cookies=cookies,
            cookies_from_browser=cookies_from_browser,
        )
        metadata = normalize_metadata(info, source_url)
        source = SourceInfo(
            platform="youtube",
            source_url=source_url,
            resolved_url=metadata["source"]["resolved_url"],
            source_id=metadata["source"]["source_id"],
        )
        raw_chapters = [
            item for item in info.get("chapters") or [] if isinstance(item, dict)
        ]
        source_chapters = normalize_source_chapters(
            source=source,
            chapters=raw_chapters,
        )
        write_json(output_dir / "source_chapters.json", source_chapters)
        artifacts.add("source_chapters_path", "source_chapters", "source_chapters.json")
        write_json(output_dir / "metadata.json", metadata)
        artifacts.add("metadata_path", "metadata", "metadata.json")
        capabilities.has_metadata = True
    except YtDlpUnavailable as error:
        diagnostics.add(
            code="TOOL_MISSING",
            severity="error",
            stage="metadata",
            message=str(error),
        )
    except Exception as error:  # noqa: BLE001
        _diagnose_command_failure(
            diagnostics,
            code="METADATA_UNAVAILABLE",
            severity="error",
            stage="metadata",
            error=error,
        )

    transcript_segments: list[dict[str, Any]] = []
    subtitle_unavailable = False
    manual_subtitles_available = False
    subtitle_language_hint = ""
    if info is not None:
        try:
            manual_subtitles_available = _has_manual_subtitles(info)
            subtitle_files = write_subtitles(
                source_url,
                raw_dir,
                source.source_id or None,
                cookies=cookies,
                cookies_from_browser=cookies_from_browser,
            )
            subtitle_file = select_subtitle_file(subtitle_files)
            subtitle_language_hint = subtitle_file.name if subtitle_file else ""
            if subtitle_file:
                transcript_segments = parse_subtitle(subtitle_file)
            if transcript_segments:
                _write_transcript_artifacts(
                    output_dir=output_dir,
                    artifacts=artifacts,
                    source=source,
                    segments=transcript_segments,
                    language=subtitle_file.name if subtitle_file else "",
                    transcript_source=_subtitle_transcript_source(info),
                )
                capabilities.has_transcript = True
            else:
                subtitle_unavailable = True
        except Exception as error:  # noqa: BLE001
            _diagnose_command_failure(
                diagnostics,
                code="TRANSCRIPT_UNAVAILABLE",
                severity="warning",
                stage="transcript",
                error=error,
            )

    comments_payload: dict[str, Any] | None = None
    if fetch_comments and info is not None:
        try:
            comment_info = dump_single_json(
                source_url,
                write_comments=True,
                max_comments=max_comments,
                comment_sort=comment_sort,
                cookies=cookies,
                cookies_from_browser=cookies_from_browser,
                timeout_seconds=360,
            )
            comments_payload = normalize_comments(
                source_id=source.source_id,
                url=source.source_url,
                raw_comments=comment_info.get("comments") or [],
                max_comments=max_comments,
            )
            write_json(output_dir / "comments.json", comments_payload)
            artifacts.add("comments_path", "comments", "comments.json")
            capabilities.has_comments = True
        except Exception as error:  # noqa: BLE001
            _diagnose_command_failure(
                diagnostics,
                code="COMMENTS_UNAVAILABLE",
                severity="warning",
                stage="comments",
                error=error,
            )
    elif fetch_comments:
        diagnostics.add(
            code="COMMENTS_UNAVAILABLE",
            severity="warning",
            stage="comments",
            message="Comments were requested but metadata extraction failed first.",
        )

    if info is not None:
        try:
            working_video = download_working_video(
                source_url,
                raw_media_dir,
                source_id=source.source_id or "youtube-video",
                max_height=1080,
                cookies=cookies,
                cookies_from_browser=cookies_from_browser,
            )
            artifacts.add(
                "working_video_path",
                "raw_media",
                working_video.relative_to(output_dir).as_posix(),
            )
            should_compare_auto_subtitles = (
                compare_auto_subtitles
                and transcript_segments
                and not manual_subtitles_available
                and not force_transcription
            )
            should_transcribe = (
                force_transcription or not transcript_segments or should_compare_auto_subtitles
            )
            if should_transcribe:
                try:
                    local_transcription_language = _infer_local_transcription_language(
                        info=info,
                        subtitle_language_hint=subtitle_language_hint,
                    )
                    transcription_info, transcribed_segments = _run_local_transcription(
                        source_url=source_url,
                        source=source,
                        output_dir=output_dir,
                        artifacts=artifacts,
                        raw_audio_dir=raw_audio_dir,
                        raw_transcription_dir=raw_transcription_dir,
                        language=local_transcription_language,
                        cookies=cookies,
                        cookies_from_browser=cookies_from_browser,
                    )
                    if transcribed_segments:
                        model_path = transcription_info.get("model_path")
                        model_path = model_path if isinstance(model_path, Path) else None
                        if should_compare_auto_subtitles:
                            _write_transcript_alternative_artifacts(
                                output_dir=output_dir,
                                artifacts=artifacts,
                                source=source,
                                primary_transcript_path="transcript.segments.json",
                                segments=transcribed_segments,
                                language=str(transcription_info.get("language") or "auto"),
                                transcript_source=str(
                                    transcription_info.get("transcript_source")
                                    or transcription_info.get("engine")
                                    or "local_transcription"
                                ),
                                reason="auto_subtitle_comparison",
                                model_path=model_path,
                                language_detection=transcription_info.get(
                                    "language_detection"
                                )
                                if isinstance(
                                    transcription_info.get("language_detection"), dict
                                )
                                else None,
                            )
                            diagnostics.add(
                                code="AUTO_SUBTITLE_COMPARISON",
                                severity="info",
                                stage="audio_transcription",
                                message=(
                                    "YouTube subtitles appear to be automatic; "
                                    "a local transcription comparison transcript was written."
                                ),
                                details={
                                    "transcript_alternatives_path": (
                                        "transcript.alternatives.json"
                                    ),
                                    "segment_count": len(transcribed_segments),
                                },
                            )
                            write_transcript_comparison(
                                bundle_dir=output_dir,
                                artifacts=artifacts,
                            )
                        else:
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
                                language_detection=transcription_info.get(
                                    "language_detection"
                                )
                                if isinstance(
                                    transcription_info.get("language_detection"), dict
                                )
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
                    if subtitle_unavailable:
                        diagnostics.add(
                            code="TRANSCRIPT_UNAVAILABLE",
                            severity="warning",
                            stage="transcript",
                            message=(
                                "yt-dlp did not produce usable subtitles and audio "
                                "transcription failed."
                            ),
                        )
            if visual_recall != "none":
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
                capabilities.has_slides = True
        except FileNotFoundError as error:
            message = str(error).lower()
            if "ffmpeg" in message:
                code = "FFMPEG_NOT_FOUND"
            elif "ffprobe" in message:
                code = "FFPROBE_FAILED"
            else:
                code = "VIDEO_FILE_UNAVAILABLE"
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
    else:
        diagnostics.add(
            code="VIDEO_FILE_UNAVAILABLE",
            severity="error",
            stage="visual_recall",
            message="Visual recall requires metadata extraction to resolve the YouTube source.",
        )

    audience_feedback = build_audience_feedback(
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
            "provider": "youtube",
            "comments": fetch_comments,
            "max_comments": max_comments,
            "comment_sort": comment_sort,
            "visual_recall": visual_recall,
            "visual_strategy": visual_strategy,
            "max_screenshots": max_screenshots,
            "force_transcription": force_transcription,
            "compare_auto_subtitles": compare_auto_subtitles,
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
        "diagnostics_path": str(output_dir / "diagnostics.json"),
        "readiness": readiness,
        "capabilities": bundle.capabilities.model_dump(mode="json"),
    }
