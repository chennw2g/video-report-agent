from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any, Literal

from video_bundle_agent.bundle.schema import SourceInfo
from video_bundle_agent.media.ffmpeg import ffprobe_data
from video_bundle_agent.media.frame_extractor import (
    FrameCandidate,
    apply_candidate_cap,
    detect_scene_change_timestamps,
    extract_fixed_interval_frames,
    extract_frame_candidates,
    fixed_interval_candidates,
    fixed_interval_timestamps,
    interval_for_visual_recall,
    keyword_trigger_candidates,
    scene_change_candidates,
)


def _parse_frame_rate(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return None


def probe_video_info(video_path: Path) -> dict[str, Any]:
    data = ffprobe_data(video_path)
    format_data = data.get("format") or {}
    video_stream = next(
        (stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"),
        {},
    )
    duration = video_stream.get("duration") or format_data.get("duration") or 0
    return {
        "path": video_path,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "duration": float(duration or 0),
        "frame_rate": _parse_frame_rate(
            video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
        ),
        "codec_name": video_stream.get("codec_name"),
        "format_name": format_data.get("format_name"),
        "size_bytes": video_path.stat().st_size if video_path.exists() else None,
    }


VisualStrategy = Literal["auto", "fixed", "keyword", "scene", "all"]


def resolve_visual_strategies(*, visual_recall: str, visual_strategy: str) -> list[str]:
    if visual_strategy == "fixed":
        return ["fixed_interval"]
    if visual_strategy == "keyword":
        return ["fixed_interval", "keyword_trigger"]
    if visual_strategy == "scene":
        return ["fixed_interval", "scene_change"]
    if visual_strategy == "all":
        return ["fixed_interval", "keyword_trigger", "scene_change"]
    if visual_strategy != "auto":
        raise ValueError(f"Unsupported visual strategy: {visual_strategy}")
    if visual_recall == "low":
        return ["fixed_interval"]
    if visual_recall == "medium":
        return ["fixed_interval", "keyword_trigger"]
    return ["fixed_interval", "keyword_trigger", "scene_change"]


def _keyword_budget(visual_recall: str, max_screenshots: int) -> int:
    if max_screenshots <= 0:
        if visual_recall == "low":
            return 10
        if visual_recall == "high":
            return 80
        return 30
    if visual_recall == "low":
        return min(10, max_screenshots)
    if visual_recall == "high":
        return min(80, max_screenshots)
    return min(30, max_screenshots)


def _scene_budget(visual_recall: str, max_screenshots: int) -> int:
    if max_screenshots <= 0:
        if visual_recall == "high":
            return 80
        return 40
    if visual_recall == "high":
        return min(80, max_screenshots)
    return min(40, max_screenshots)


def _candidate_cap(max_screenshots: int) -> int | None:
    if max_screenshots <= 0:
        return None
    return max_screenshots


def _timestamp_span(candidates: list[FrameCandidate]) -> dict[str, float | None]:
    if not candidates:
        return {"first_timestamp": None, "last_timestamp": None}
    timestamps = [candidate.timestamp for candidate in candidates]
    return {
        "first_timestamp": min(timestamps),
        "last_timestamp": max(timestamps),
    }


def _visual_coverage_warning(
    *,
    max_screenshots: int,
    expected_fixed_interval_count: int,
    candidate_count: int,
    skipped_due_to_cap: int,
) -> dict[str, Any] | None:
    if skipped_due_to_cap <= 0:
        return None
    return {
        "code": "VISUAL_COVERAGE_TRUNCATED",
        "severity": "warning",
        "stage": "visual_recall",
        "message": (
            "Screenshot candidate coverage was truncated by --max-screenshots. "
            "Use --max-screenshots 0 for full fixed-interval coverage."
        ),
        "details": {
            "max_screenshots": max_screenshots,
            "candidate_count": candidate_count,
            "expected_fixed_interval_count": expected_fixed_interval_count,
            "skipped_due_to_cap": skipped_due_to_cap,
        },
    }


def _normalize_extracted_items(
    *,
    extracted: list[dict[str, object]],
    output_dir: Path,
) -> tuple[list[dict[str, Any]], list[Path]]:
    screenshot_paths: list[Path] = []
    items: list[dict[str, Any]] = []
    for item in extracted:
        path = item["path"]
        if not isinstance(path, Path):
            continue
        screenshot_paths.append(path)
        normalized = dict(item)
        normalized["path"] = path.relative_to(output_dir).as_posix()
        items.append(normalized)
    return items, screenshot_paths


def create_visual_recall_slides(
    *,
    source: SourceInfo,
    source_url: str,
    video_path: Path,
    output_dir: Path,
    visual_recall: str,
    max_screenshots: int,
    visual_strategy: str = "auto",
    transcript_segments: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[Path], list[dict[str, Any]]]:
    video_info = probe_video_info(video_path)
    interval_seconds = interval_for_visual_recall(visual_recall)
    strategies = resolve_visual_strategies(
        visual_recall=visual_recall,
        visual_strategy=visual_strategy,
    )
    fixed_candidates, fixed_sampled_due_to_cap, fixed_skipped_count = fixed_interval_candidates(
        duration=video_info["duration"],
        interval_seconds=interval_seconds,
        max_screenshots=max_screenshots,
    )
    candidates: list[FrameCandidate] = list(fixed_candidates)
    warnings: list[dict[str, Any]] = []

    keyword_candidates: list[FrameCandidate] = []
    keyword_skipped_count = 0
    if "keyword_trigger" in strategies and transcript_segments:
        keyword_candidates, keyword_skipped_count = keyword_trigger_candidates(
            segments=transcript_segments,
            duration=video_info["duration"],
            max_candidates=_keyword_budget(visual_recall, max_screenshots),
        )
        candidates.extend(keyword_candidates)

    scene_timestamps: list[float] = []
    scene_status = "not_run"
    if "scene_change" in strategies:
        try:
            scene_timestamps = detect_scene_change_timestamps(
                video_path=video_path,
                duration=video_info["duration"],
                max_scenes=_scene_budget(visual_recall, max_screenshots),
            )
            scene_status = "ok"
            candidates.extend(scene_change_candidates(timestamps=scene_timestamps))
        except Exception as error:  # noqa: BLE001
            scene_status = "failed"
            warnings.append(
                {
                    "code": "FRAME_EXTRACTION_FAILED",
                    "severity": "warning",
                    "stage": "visual_recall_scene",
                    "message": f"Scene-change detection failed: {error}",
                    "details": {"exception": type(error).__name__},
                }
            )

    planned_count_before_cap = len(candidates) + fixed_skipped_count
    capped_candidates, mixed_skipped_count = apply_candidate_cap(
        candidates,
        max_candidates=max_screenshots,
    )
    skipped_due_to_cap = fixed_skipped_count + mixed_skipped_count
    expected_fixed_interval_count = len(fixed_candidates) + fixed_skipped_count
    coverage_truncated = skipped_due_to_cap > 0
    coverage_warning = _visual_coverage_warning(
        max_screenshots=max_screenshots,
        expected_fixed_interval_count=expected_fixed_interval_count,
        candidate_count=len(capped_candidates),
        skipped_due_to_cap=skipped_due_to_cap,
    )
    if coverage_warning:
        warnings.append(coverage_warning)

    candidates_dir = output_dir / "screenshots" / "candidates"
    extracted = extract_frame_candidates(
        video_path=video_path,
        output_dir=candidates_dir,
        candidates=capped_candidates,
    )

    items, screenshot_paths = _normalize_extracted_items(
        extracted=extracted,
        output_dir=output_dir,
    )

    slides = {
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "url": source_url,
        },
        "video": {
            "path": video_path.relative_to(output_dir).as_posix(),
            "width": video_info["width"],
            "height": video_info["height"],
            "duration": video_info["duration"],
            "frame_rate": video_info["frame_rate"],
            "codec_name": video_info["codec_name"],
            "format_name": video_info["format_name"],
            "size_bytes": video_info["size_bytes"],
        },
        "extraction": {
            "strategy": "mixed" if len(strategies) > 1 else strategies[0],
            "strategies": strategies,
            "visual_strategy": visual_strategy,
            "visual_recall": visual_recall,
            "interval_seconds": interval_seconds,
            "max_screenshots": max_screenshots,
            "candidate_cap": _candidate_cap(max_screenshots),
            "candidate_cap_unlimited": max_screenshots <= 0,
            "candidate_count": len(items),
            "planned_count_before_cap": planned_count_before_cap,
            "sampled_due_to_cap": coverage_truncated,
            "skipped_due_to_cap": skipped_due_to_cap,
            "coverage": {
                "duration": video_info["duration"],
                "interval_seconds": interval_seconds,
                "expected_fixed_interval_count": expected_fixed_interval_count,
                "fixed_interval_coverage_complete": not coverage_truncated,
                "candidate_cap_unlimited": max_screenshots <= 0,
                "coverage_truncated": coverage_truncated,
                **_timestamp_span(capped_candidates),
            },
            "fixed_interval": {
                "candidate_count": len(fixed_candidates),
                "sampled_due_to_cap": fixed_sampled_due_to_cap,
                "skipped_due_to_cap": fixed_skipped_count,
            },
            "keyword_trigger": {
                "enabled": "keyword_trigger" in strategies,
                "candidate_count": len(keyword_candidates),
                "skipped_count": keyword_skipped_count,
            },
            "scene_change": {
                "enabled": "scene_change" in strategies,
                "status": scene_status,
                "candidate_count": len(scene_timestamps),
                "threshold": 0.35,
            },
            "ocr_enabled": False,
            "ocr_status": "not_run",
        },
        "items": items,
    }
    return slides, screenshot_paths, warnings


def create_fixed_interval_slides(
    *,
    source: SourceInfo,
    source_url: str,
    video_path: Path,
    output_dir: Path,
    visual_recall: str,
    max_screenshots: int,
) -> tuple[dict[str, Any], list[Path]]:
    video_info = probe_video_info(video_path)
    interval_seconds = interval_for_visual_recall(visual_recall)
    timestamps, sampled_due_to_cap, skipped_count = fixed_interval_timestamps(
        duration=video_info["duration"],
        interval_seconds=interval_seconds,
        max_screenshots=max_screenshots,
    )
    candidates_dir = output_dir / "screenshots" / "candidates"
    extracted = extract_fixed_interval_frames(
        video_path=video_path,
        output_dir=candidates_dir,
        timestamps=timestamps,
    )
    items, screenshot_paths = _normalize_extracted_items(
        extracted=extracted,
        output_dir=output_dir,
    )
    slides = {
        "source": {
            "platform": source.platform,
            "source_id": source.source_id,
            "url": source_url,
        },
        "video": {
            "path": video_path.relative_to(output_dir).as_posix(),
            "width": video_info["width"],
            "height": video_info["height"],
            "duration": video_info["duration"],
            "frame_rate": video_info["frame_rate"],
            "codec_name": video_info["codec_name"],
            "format_name": video_info["format_name"],
            "size_bytes": video_info["size_bytes"],
        },
        "extraction": {
            "strategy": "fixed_interval",
            "strategies": ["fixed_interval"],
            "visual_strategy": "fixed",
            "visual_recall": visual_recall,
            "interval_seconds": interval_seconds,
            "max_screenshots": max_screenshots,
            "candidate_cap": _candidate_cap(max_screenshots),
            "candidate_cap_unlimited": max_screenshots <= 0,
            "candidate_count": len(items),
            "sampled_due_to_cap": sampled_due_to_cap,
            "skipped_due_to_cap": skipped_count,
            "coverage": {
                "duration": video_info["duration"],
                "interval_seconds": interval_seconds,
                "expected_fixed_interval_count": len(timestamps) + skipped_count,
                "fixed_interval_coverage_complete": not sampled_due_to_cap,
                "candidate_cap_unlimited": max_screenshots <= 0,
                "coverage_truncated": sampled_due_to_cap,
                "first_timestamp": min(timestamps) if timestamps else None,
                "last_timestamp": max(timestamps) if timestamps else None,
            },
            "ocr_enabled": False,
            "ocr_status": "not_run",
        },
        "items": items,
    }
    return slides, screenshot_paths
