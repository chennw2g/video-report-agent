from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from video_bundle_agent.media.ffmpeg import extract_audio_wav
from video_bundle_agent.media.transcription import (
    build_transcript_payload,
    transcribe_audio_for_language,
)
from video_bundle_agent.media.visual_recall import create_visual_recall_slides, probe_video_info


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_media_name(path: Path) -> str:
    stem = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in path.stem)
    stem = stem.strip("._") or "local_video"
    suffix = path.suffix.lower() or ".mp4"
    return f"{stem}{suffix}"


def _copy_working_video(source_path: Path, output_dir: Path) -> Path:
    raw_media_dir = output_dir / "raw" / "media"
    raw_media_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_media_dir / _safe_media_name(source_path)
    if source_path.resolve() != destination.resolve():
        shutil.copy2(source_path, destination)
    return destination


def _metadata_from_video(
    *,
    source: SourceInfo,
    source_path: Path,
    working_video: Path,
    output_dir: Path,
) -> dict[str, Any]:
    info = probe_video_info(working_video)
    return {
        "source": source.model_dump(mode="json"),
        "fetched_at": _utc_now(),
        "title": source_path.stem,
        "description": "",
        "duration": info.get("duration"),
        "published_at": "",
        "updated_at": "",
        "uploader": "",
        "uploader_id": "",
        "channel": "",
        "channel_id": "",
        "view_count": None,
        "like_count": None,
        "comment_count": None,
        "share_count": None,
        "thumbnail": "",
        "tags": [],
        "categories": ["local_video"],
        "availability": "local",
        "extractor": "local_video",
        "local_path": str(source_path),
        "working_video_path": working_video.relative_to(output_dir).as_posix(),
        "width": info.get("width"),
        "height": info.get("height"),
        "frame_rate": info.get("frame_rate"),
        "codec_name": info.get("codec_name"),
        "format_name": info.get("format_name"),
        "size_bytes": info.get("size_bytes"),
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
    payload = build_transcript_payload(
        source=source.model_dump(mode="json"),
        segments=segments,
        language=language,
        transcript_source=transcript_source,
        model_path=model_path,
        language_detection=language_detection,
    )
    write_json(output_dir / "transcript.segments.json", payload)
    write_text(
        output_dir / "transcript.txt",
        "\n".join(str(segment.get("text") or "") for segment in segments).strip() + "\n",
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


def _build_audience_feedback(source: SourceInfo) -> dict[str, Any]:
    return {
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "url": source.source_url,
        },
        "fetched_at": _utc_now(),
        "has_comments": False,
        "count_fetched": 0,
        "summary": "Local video input does not provide platform audience feedback.",
        "stats": {
            "top_liked": [],
            "top_replied": [],
            "top_terms": [],
            "question_comments": [],
            "critical_comments": [],
            "supportive_comments": [],
        },
    }


def _diagnose_failure(
    diagnostics: DiagnosticLog,
    *,
    code: str,
    severity: str,
    stage: str,
    error: Exception,
) -> None:
    diagnostics.add(
        code=code,
        severity=severity,  # type: ignore[arg-type]
        stage=stage,
        message=str(error),
        details={"exception": type(error).__name__},
    )


def analyze_local_video(
    source_path: str,
    output_dir: Path,
    *,
    visual_recall: str = "medium",
    visual_strategy: str = "auto",
    max_screenshots: int = 0,
    force_transcription: bool = False,
) -> dict[str, Any]:
    timings = StageTimings()
    diagnostics = DiagnosticLog()
    artifacts = BundleArtifacts()
    capabilities = Capabilities(has_danmaku=False)
    input_path = Path(source_path).expanduser().resolve()
    source = SourceInfo(
        platform="local_video",
        source_url=str(input_path),
        resolved_url=str(input_path),
        source_id=input_path.stem,
    )

    working_video: Path | None = None
    transcript_segments: list[dict[str, Any]] = []

    try:
        with timings.stage("media_import"):
            if not input_path.exists() or not input_path.is_file():
                raise FileNotFoundError(f"Local video file was not found: {input_path}")
            working_video = _copy_working_video(input_path, output_dir)
            artifacts.add(
                "working_video_path",
                "raw_media",
                working_video.relative_to(output_dir).as_posix(),
            )
    except Exception as error:  # noqa: BLE001
        _diagnose_failure(
            diagnostics,
            code="VIDEO_FILE_UNAVAILABLE",
            severity="error",
            stage="media_import",
            error=error,
        )

    if working_video is not None:
        try:
            with timings.stage("metadata"):
                metadata = _metadata_from_video(
                    source=source,
                    source_path=input_path,
                    working_video=working_video,
                    output_dir=output_dir,
                )
                write_json(output_dir / "metadata.json", metadata)
                artifacts.add("metadata_path", "metadata", "metadata.json")
                capabilities.has_metadata = True
        except FileNotFoundError as error:
            _diagnose_failure(
                diagnostics,
                code="FFPROBE_FAILED",
                severity="error",
                stage="metadata",
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

    if working_video is not None and (force_transcription or not transcript_segments):
        try:
            with timings.stage("audio_transcription"):
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
                transcription_info, transcript_segments = transcribe_audio_for_language(
                    wav_path,
                    raw_transcription_dir,
                    language="auto",
                )
                _add_transcription_info_artifacts(
                    output_dir=output_dir,
                    artifacts=artifacts,
                    transcription_info=transcription_info,
                )
                if transcript_segments:
                    model_path = transcription_info.get("model_path")
                    model_path = model_path if isinstance(model_path, Path) else None
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
        except FileNotFoundError as error:
            message = str(error).lower()
            code = "FFMPEG_NOT_FOUND" if "ffmpeg" in message else "TRANSCRIPTION_UNAVAILABLE"
            _diagnose_failure(
                diagnostics,
                code=code,
                severity="warning",
                stage="audio_transcription",
                error=error,
            )
        except Exception as error:  # noqa: BLE001
            _diagnose_failure(
                diagnostics,
                code="TRANSCRIPTION_UNAVAILABLE",
                severity="warning",
                stage="audio_transcription",
                error=error,
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
            _diagnose_failure(
                diagnostics,
                code=code,
                severity="error",
                stage="visual_recall",
                error=error,
            )
        except Exception as error:  # noqa: BLE001
            _diagnose_failure(
                diagnostics,
                code="FRAME_EXTRACTION_FAILED",
                severity="error",
                stage="visual_recall",
                error=error,
            )

    with timings.stage("audience_feedback"):
        write_json(output_dir / "audience_feedback.json", _build_audience_feedback(source))
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
            "provider": "local_video",
            "source_path": str(input_path),
            "visual_recall": visual_recall,
            "visual_strategy": visual_strategy,
            "max_screenshots": max_screenshots,
            "force_transcription": force_transcription,
            "no_llm": True,
        },
    )
    readiness = evaluate_bundle_readiness(output_dir)
    return {
        "status": diagnostics.status,
        "report_ready": readiness["report_ready"],
        "output_dir": str(output_dir),
        "bundle_path": str(output_dir / "bundle.json"),
        "metadata_path": str(output_dir / "metadata.json") if bundle.metadata_path else None,
        "transcript_path": str(output_dir / "transcript.segments.json")
        if bundle.transcript_path
        else None,
        "comments_path": str(output_dir / "comments.json") if bundle.comments_path else None,
        "audience_feedback_path": str(output_dir / "audience_feedback.json"),
        "slides_path": str(output_dir / "slides.json") if bundle.slides_path else None,
        "timings_path": str(output_dir / "timings.json"),
        "diagnostics_path": str(output_dir / "diagnostics.json"),
    }
