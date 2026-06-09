from __future__ import annotations

import difflib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from video_bundle_agent.bundle.schema import BundleIndex, Capabilities, Manifest, SourceInfo
from video_bundle_agent.bundle.writer import BundleArtifacts, finalize_bundle, write_json
from video_bundle_agent.diagnostics.models import DiagnosticLog

TECHNICAL_TERMS = (
    "ai",
    "chip",
    "chips",
    "compute",
    "computer",
    "co-design",
    "code design",
    "data center",
    "energy",
    "euv",
    "gpu",
    "hbm",
    "hbm2",
    "huawei",
    "inference",
    "memory",
    "nvidia",
    "performance",
    "silicon",
    "throughput",
    "watt",
)

ARTIFACT_FIELD_KINDS: dict[str, str] = {
    "metadata_path": "metadata",
    "transcript_path": "transcript",
    "transcript_text_path": "transcript_text",
    "transcript_alternatives_path": "transcript_alternatives",
    "transcript_comparison_path": "transcript_comparison",
    "comments_path": "comments",
    "danmaku_path": "danmaku",
    "audience_feedback_path": "audience_feedback",
    "slides_path": "slides",
    "working_video_path": "raw_media",
    "working_audio_path": "raw_audio",
    "content_profile_path": "content_profile",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _segment_start(segment: dict[str, Any]) -> float:
    return float(segment.get("start") or 0)


def _segment_end(segment: dict[str, Any]) -> float:
    end = segment.get("end")
    if end is not None:
        return float(end)
    return _segment_start(segment)


def _segment_text(segment: dict[str, Any]) -> str:
    return re.sub(r"\s+", " ", str(segment.get("text") or "")).strip()


def _window_text(
    segments: list[dict[str, Any]],
    *,
    start: float,
    end: float,
) -> str:
    texts: list[str] = []
    for segment in segments:
        segment_start = _segment_start(segment)
        segment_end = _segment_end(segment)
        if segment_end < start or segment_start > end:
            continue
        text = _segment_text(segment)
        if text:
            texts.append(text)
    return " ".join(texts)


def _normalize_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?|[\u4e00-\u9fff]+", text.lower())


def _term_hits(text: str, terms: tuple[str, ...] = TECHNICAL_TERMS) -> list[str]:
    lower_text = text.lower()
    hits: list[str] = []
    for term in terms:
        pattern = rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])"
        if re.search(pattern, lower_text) and term not in hits:
            hits.append(term)
    return hits


def _diff_summary(primary: str, alternative: str, *, limit: int = 14) -> dict[str, list[str]]:
    primary_words = _normalize_words(primary)
    alternative_words = _normalize_words(alternative)
    removed: list[str] = []
    added: list[str] = []
    matcher = difflib.SequenceMatcher(
        a=primary_words,
        b=alternative_words,
        autojunk=False,
    )
    for opcode, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if opcode in {"replace", "delete"}:
            removed.extend(primary_words[a_start:a_end])
        if opcode in {"replace", "insert"}:
            added.extend(alternative_words[b_start:b_end])
        if len(removed) >= limit and len(added) >= limit:
            break
    return {
        "primary_only": removed[:limit],
        "alternative_only": added[:limit],
    }


def _comparison_windows(
    primary_segments: list[dict[str, Any]],
    *,
    window_seconds: int,
) -> list[tuple[float, float]]:
    if not primary_segments:
        return []
    duration = max(_segment_end(segment) for segment in primary_segments)
    if duration <= 0:
        return [(0.0, float(window_seconds))]
    windows: list[tuple[float, float]] = []
    current = 0.0
    while current < duration:
        windows.append((round(current, 1), round(min(duration, current + window_seconds), 1)))
        current += window_seconds
    return windows


def compare_transcript_segments(
    *,
    source: dict[str, Any],
    primary: dict[str, Any],
    alternative: dict[str, Any],
    alternative_path: str,
    window_seconds: int = 15,
    min_similarity_to_flag: float = 0.88,
) -> dict[str, Any]:
    primary_segments = primary.get("segments") or []
    alternative_segments = alternative.get("segments") or []
    items: list[dict[str, Any]] = []
    flagged_count = 0

    for start, end in _comparison_windows(primary_segments, window_seconds=window_seconds):
        primary_text = _window_text(primary_segments, start=start, end=end)
        alternative_text = _window_text(alternative_segments, start=start, end=end)
        if not primary_text and not alternative_text:
            continue
        similarity = difflib.SequenceMatcher(
            a=_normalize_words(primary_text),
            b=_normalize_words(alternative_text),
            autojunk=False,
        ).ratio()
        primary_terms = _term_hits(primary_text)
        alternative_terms = _term_hits(alternative_text)
        term_differences = {
            "primary_only": [term for term in primary_terms if term not in alternative_terms],
            "alternative_only": [term for term in alternative_terms if term not in primary_terms],
        }
        flagged = similarity < min_similarity_to_flag or bool(
            term_differences["primary_only"] or term_differences["alternative_only"]
        )
        if flagged:
            flagged_count += 1
        items.append(
            {
                "start": start,
                "end": end,
                "similarity": round(similarity, 4),
                "flagged": flagged,
                "primary_text": primary_text,
                "alternative_text": alternative_text,
                "term_differences": term_differences,
                "word_differences": _diff_summary(primary_text, alternative_text),
            }
        )

    return {
        "schema_version": "0.1.0",
        "source": source,
        "generated_at": datetime.now(UTC).isoformat(),
        "primary": {
            "transcript_source": primary.get("transcript_source"),
            "language": primary.get("language"),
            "segment_count": len(primary_segments),
            "path": "transcript.segments.json",
        },
        "alternative": {
            "transcript_source": alternative.get("transcript_source"),
            "language": alternative.get("language"),
            "segment_count": len(alternative_segments),
            "path": alternative_path,
            "model_path": alternative.get("model_path"),
        },
        "comparison": {
            "window_seconds": window_seconds,
            "window_count": len(items),
            "flagged_window_count": flagged_count,
            "min_similarity_to_flag": min_similarity_to_flag,
        },
        "items": items,
    }


def write_transcript_comparison(
    *,
    bundle_dir: Path,
    artifacts: BundleArtifacts | None = None,
    window_seconds: int = 15,
) -> dict[str, Any] | None:
    bundle_path = bundle_dir / "bundle.json"
    if bundle_path.exists():
        bundle = _read_json(bundle_path)
        alternatives_path = bundle.get("transcript_alternatives_path")
        primary_path = bundle.get("transcript_path")
        source = bundle.get("source") or {}
    else:
        bundle = {}
        alternatives_path = "transcript.alternatives.json"
        primary_path = "transcript.segments.json"
        source = {}
    if not primary_path or not alternatives_path:
        return None
    if not (bundle_dir / primary_path).exists() or not (bundle_dir / alternatives_path).exists():
        return None
    alternatives = _read_json(bundle_dir / alternatives_path)
    items = alternatives.get("items") or []
    if not items:
        return None
    first = items[0]
    alternative_path = first.get("transcript_path")
    if not alternative_path:
        return None

    primary = _read_json(bundle_dir / primary_path)
    source = source or primary.get("source") or alternatives.get("source") or {}
    alternative = _read_json(bundle_dir / alternative_path)
    payload = compare_transcript_segments(
        source=source,
        primary=primary,
        alternative=alternative,
        alternative_path=str(alternative_path),
        window_seconds=window_seconds,
    )
    write_json(bundle_dir / "transcript.comparison.json", payload)
    if artifacts is not None:
        artifacts.add(
            "transcript_comparison_path",
            "transcript_comparison",
            "transcript.comparison.json",
        )
    return payload


def _collect_existing_artifacts(bundle_dir: Path, bundle: BundleIndex) -> BundleArtifacts:
    artifacts = BundleArtifacts()
    for field, kind in ARTIFACT_FIELD_KINDS.items():
        relative_path = getattr(bundle, field, None)
        if relative_path and (bundle_dir / relative_path).exists():
            artifacts.add(field, kind, relative_path)

    manifest_path = bundle_dir / bundle.manifest_path
    if manifest_path.exists():
        manifest = Manifest.model_validate(_read_json(manifest_path))
        for index, file in enumerate(manifest.files, start=1):
            if not (bundle_dir / file.path).exists():
                continue
            if file.path in artifacts.kinds:
                continue
            artifacts.add(f"manifest_file_{index:04d}", file.kind, file.path)
    return artifacts


def compare_transcripts_for_bundle(bundle_dir: Path, *, window_seconds: int = 15) -> dict[str, Any]:
    bundle = None
    artifacts = None
    bundle_path = bundle_dir / "bundle.json"
    if bundle_path.exists():
        bundle = BundleIndex.model_validate(_read_json(bundle_path))
        artifacts = _collect_existing_artifacts(bundle_dir, bundle)

    payload = write_transcript_comparison(
        bundle_dir=bundle_dir,
        artifacts=artifacts,
        window_seconds=window_seconds,
    )
    if payload is None:
        return {
            "schema_version": "0.1.0",
            "bundle_dir": str(bundle_dir),
            "written": False,
            "message": "No transcript alternatives were available to compare.",
        }
    if bundle is not None and artifacts is not None:
        diagnostics_path = bundle_dir / bundle.diagnostics_path
        diagnostics = (
            DiagnosticLog.model_validate(_read_json(diagnostics_path))
            if diagnostics_path.exists()
            else DiagnosticLog()
        )
        updated_bundle = finalize_bundle(
            output_dir=bundle_dir,
            source=SourceInfo.model_validate(bundle.source.model_dump(mode="json")),
            artifacts=artifacts,
            capabilities=Capabilities.model_validate(bundle.capabilities.model_dump(mode="json")),
            diagnostics=diagnostics,
            command={
                "operation": "compare_transcripts",
                "window_seconds": window_seconds,
            },
        )
        bundle_path_value = str(bundle_dir / "bundle.json")
        comparison_path = updated_bundle.transcript_comparison_path
    else:
        bundle_path_value = None
        comparison_path = "transcript.comparison.json"
    return {
        "schema_version": "0.1.0",
        "bundle_dir": str(bundle_dir),
        "written": True,
        "path": str(bundle_dir / str(comparison_path)),
        "bundle_path": bundle_path_value,
        "comparison": payload["comparison"],
    }
