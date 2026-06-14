from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from video_bundle_agent.bundle.readiness import evaluate_bundle_readiness
from video_bundle_agent.bundle.schema import (
    BundleIndex,
    Capabilities,
    Manifest,
    SourceInfo,
)
from video_bundle_agent.bundle.timings import StageTimings
from video_bundle_agent.bundle.writer import BundleArtifacts, finalize_bundle, write_json
from video_bundle_agent.diagnostics.models import DiagnosticLog
from video_bundle_agent.media.visual_recall import create_visual_recall_slides

_BUNDLE_ARTIFACT_FIELDS: dict[str, str] = {
    "metadata_path": "metadata",
    "transcript_path": "transcript",
    "transcript_text_path": "transcript_text",
    "transcript_alternatives_path": "transcript_alternatives",
    "transcript_comparison_path": "transcript_comparison",
    "comments_path": "comments",
    "danmaku_path": "danmaku",
    "audience_feedback_path": "audience_feedback",
    "media_path": "media",
    "thumbnail_path": "thumbnail",
    "slides_path": "slides",
    "working_video_path": "raw_media",
    "working_audio_path": "raw_audio",
    "content_profile_path": "content_profile",
    "timings_path": "timings",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_plan_path(bundle_dir: Path, plan_path: Path | None) -> Path | None:
    if plan_path is None:
        candidate = bundle_dir / "visual_selection_plan.json"
        return candidate if candidate.exists() else None
    candidate = plan_path if plan_path.is_absolute() else bundle_dir / plan_path
    return candidate if candidate.exists() else None


def _load_visual_plan(
    bundle_dir: Path,
    plan_path: Path | None,
) -> tuple[dict[str, Any] | None, str | None]:
    resolved = _resolve_plan_path(bundle_dir, plan_path)
    if resolved is None:
        return None, None
    try:
        relative_path = _relative_to_bundle(bundle_dir, resolved)
    except ValueError:
        relative_path = str(resolved)
    return _read_json(resolved), relative_path


def _load_bundle(bundle_dir: Path) -> BundleIndex:
    return BundleIndex.model_validate(_read_json(bundle_dir / "bundle.json"))


def _load_manifest(bundle_dir: Path, bundle: BundleIndex) -> Manifest:
    path = bundle_dir / bundle.manifest_path
    if not path.exists():
        return Manifest(source=bundle.source, files=[], diagnostics_summary={})
    return Manifest.model_validate(_read_json(path))


def _load_diagnostics(bundle_dir: Path, bundle: BundleIndex) -> DiagnosticLog:
    path = bundle_dir / bundle.diagnostics_path
    if not path.exists():
        return DiagnosticLog()
    return DiagnosticLog.model_validate(_read_json(path))


def _relative_to_bundle(bundle_dir: Path, path: Path) -> str:
    return path.relative_to(bundle_dir).as_posix()


def _collect_existing_artifacts(
    *,
    bundle_dir: Path,
    bundle: BundleIndex,
    manifest: Manifest,
) -> BundleArtifacts:
    artifacts = BundleArtifacts()
    for field, kind in _BUNDLE_ARTIFACT_FIELDS.items():
        relative_path = getattr(bundle, field, None)
        if relative_path and (bundle_dir / relative_path).exists():
            artifacts.add(field, kind, relative_path)

    for file in manifest.files:
        if not (bundle_dir / file.path).exists():
            continue
        if file.kind == "raw_media":
            artifacts.add("working_video_path", "raw_media", file.path)

    profile_path = bundle_dir / "content_profile.json"
    if profile_path.exists():
        artifacts.add("content_profile_path", "content_profile", "content_profile.json")
    return artifacts


def _find_working_video(
    *,
    bundle_dir: Path,
    bundle: BundleIndex,
    manifest: Manifest,
) -> Path | None:
    if bundle.working_video_path:
        candidate = bundle_dir / bundle.working_video_path
        if candidate.exists():
            return candidate

    for file in manifest.files:
        if file.kind != "raw_media":
            continue
        candidate = bundle_dir / file.path
        if candidate.exists():
            return candidate

    if bundle.slides_path and (bundle_dir / bundle.slides_path).exists():
        slides = _read_json(bundle_dir / bundle.slides_path)
        video_path = (slides.get("video") or {}).get("path")
        if video_path:
            candidate = bundle_dir / video_path
            if candidate.exists():
                return candidate

    raw_media_dir = bundle_dir / "raw" / "media"
    if raw_media_dir.exists():
        for candidate in sorted(raw_media_dir.iterdir()):
            if candidate.is_file() and candidate.suffix.lower() in {
                ".mp4",
                ".webm",
                ".mkv",
                ".mov",
            }:
                return candidate
    return None


def _load_transcript_segments(bundle_dir: Path, bundle: BundleIndex) -> list[dict[str, Any]]:
    if not bundle.transcript_path:
        return []
    path = bundle_dir / bundle.transcript_path
    if not path.exists():
        return []
    payload = _read_json(path)
    segments = payload.get("segments") or []
    return [segment for segment in segments if isinstance(segment, dict)]


def _has_diagnostic_code(diagnostics: DiagnosticLog, code: str) -> bool:
    return any(record.code == code for record in diagnostics.records)


def _add_visual_warnings(
    diagnostics: DiagnosticLog,
    warnings: list[dict[str, Any]],
) -> None:
    for warning in warnings:
        diagnostics.add(
            code=str(warning["code"]),
            severity=warning["severity"],  # type: ignore[arg-type]
            stage=str(warning["stage"]),
            message=str(warning["message"]),
            details=warning.get("details") or {},
        )


def _diagnostic_code_for_missing_tool(error: FileNotFoundError) -> str:
    message = str(error).lower()
    if "ffmpeg" in message:
        return "FFMPEG_NOT_FOUND"
    if "ffprobe" in message:
        return "FFPROBE_FAILED"
    return "VIDEO_FILE_UNAVAILABLE"


def _remove_stale_candidate_screenshots(
    *,
    bundle_dir: Path,
    current_screenshot_paths: list[Path],
) -> None:
    candidates_dir = (bundle_dir / "screenshots" / "candidates").resolve()
    if not candidates_dir.exists():
        return

    resolved_bundle_dir = bundle_dir.resolve()
    if not candidates_dir.is_relative_to(resolved_bundle_dir):
        return

    current_paths = {path.resolve() for path in current_screenshot_paths}
    for candidate in candidates_dir.glob("*.png"):
        resolved_candidate = candidate.resolve()
        if (
            resolved_candidate.is_file()
            and resolved_candidate.is_relative_to(candidates_dir)
            and resolved_candidate not in current_paths
        ):
            resolved_candidate.unlink()


def extract_frames_for_bundle(
    bundle_dir: Path,
    *,
    visual_recall: str,
    visual_strategy: str = "auto",
    max_screenshots: int = 0,
    plan_path: Path | None = None,
) -> dict[str, Any]:
    bundle_dir = bundle_dir.resolve()
    timings = StageTimings.load(bundle_dir / "timings.json")
    bundle = _load_bundle(bundle_dir)
    manifest = _load_manifest(bundle_dir, bundle)
    diagnostics = _load_diagnostics(bundle_dir, bundle)
    capabilities = Capabilities.model_validate(bundle.capabilities.model_dump(mode="json"))
    artifacts = _collect_existing_artifacts(
        bundle_dir=bundle_dir,
        bundle=bundle,
        manifest=manifest,
    )

    working_video = _find_working_video(bundle_dir=bundle_dir, bundle=bundle, manifest=manifest)
    screenshot_paths: list[Path] = []
    visual_plan, visual_plan_relative_path = _load_visual_plan(bundle_dir, plan_path)

    if working_video is None:
        diagnostics.add(
            code="VIDEO_FILE_UNAVAILABLE",
            severity="error",
            stage="visual_recall",
            message="No local working video was found in the bundle.",
        )
        capabilities.has_slides = False
    else:
        artifacts.add(
            "working_video_path",
            "raw_media",
            _relative_to_bundle(bundle_dir, working_video),
        )
        try:
            with timings.stage(
                "extract_frames",
                {
                    "visual_recall": visual_recall,
                    "visual_strategy": visual_strategy,
                    "max_screenshots": max_screenshots,
                    "visual_selection_plan_path": visual_plan_relative_path,
                },
            ):
                slides_payload, screenshot_paths, visual_warnings = create_visual_recall_slides(
                    source=bundle.source,
                    source_url=bundle.source.source_url,
                    video_path=working_video,
                    output_dir=bundle_dir,
                    visual_recall=visual_recall,
                    visual_strategy=visual_strategy,
                    max_screenshots=max_screenshots,
                    transcript_segments=_load_transcript_segments(bundle_dir, bundle),
                    visual_plan=visual_plan,
                )
                _add_visual_warnings(diagnostics, visual_warnings)
                _remove_stale_candidate_screenshots(
                    bundle_dir=bundle_dir,
                    current_screenshot_paths=screenshot_paths,
                )
                write_json(bundle_dir / "slides.json", slides_payload)
                artifacts.add("slides_path", "slides", "slides.json")
                for index, screenshot_path in enumerate(screenshot_paths, start=1):
                    artifacts.add(
                        f"screenshot_{index:04d}",
                        "screenshot",
                        _relative_to_bundle(bundle_dir, screenshot_path),
                    )
                capabilities.has_slides = bool(screenshot_paths)
                if not screenshot_paths:
                    diagnostics.add(
                        code="FRAME_EXTRACTION_FAILED",
                        severity="error",
                        stage="visual_recall",
                        message="Frame extraction produced no screenshots.",
                    )
        except FileNotFoundError as error:
            diagnostics.add(
                code=_diagnostic_code_for_missing_tool(error),
                severity="error",
                stage="visual_recall",
                message=str(error),
            )
            capabilities.has_slides = False
        except Exception as error:  # noqa: BLE001
            diagnostics.add(
                code="FRAME_EXTRACTION_FAILED",
                severity="error",
                stage="visual_recall",
                message=str(error),
                details={"exception": type(error).__name__},
            )
            capabilities.has_slides = False

    timings.write(bundle_dir / "timings.json")
    artifacts.add("timings_path", "timings", "timings.json")

    if diagnostics.status == "error" and not _has_diagnostic_code(diagnostics, "BUNDLE_INCOMPLETE"):
        diagnostics.add(
            code="BUNDLE_INCOMPLETE",
            severity="warning",
            stage="bundle",
            message="Bundle was written with missing required report evidence.",
        )

    updated_bundle = finalize_bundle(
        output_dir=bundle_dir,
        source=SourceInfo.model_validate(bundle.source.model_dump(mode="json")),
        artifacts=artifacts,
        capabilities=capabilities,
        diagnostics=diagnostics,
        command={
            "operation": "extract_frames",
            "visual_recall": visual_recall,
            "visual_strategy": visual_strategy,
            "max_screenshots": max_screenshots,
            "visual_selection_plan_path": visual_plan_relative_path,
        },
    )
    readiness = evaluate_bundle_readiness(bundle_dir)
    return {
        "status": diagnostics.status,
        "report_ready": readiness["report_ready"],
        "output_dir": str(bundle_dir),
        "bundle_path": str(bundle_dir / "bundle.json"),
        "slides_path": str(bundle_dir / "slides.json") if updated_bundle.slides_path else None,
        "timings_path": str(bundle_dir / "timings.json"),
        "diagnostics_path": str(bundle_dir / "diagnostics.json"),
        "screenshot_count": len(screenshot_paths),
        "readiness": readiness,
        "capabilities": updated_bundle.capabilities.model_dump(mode="json"),
    }
