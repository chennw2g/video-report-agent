from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from video_bundle_agent.bundle.evidence import select_report_evidence
from video_bundle_agent.bundle.readiness import evaluate_bundle_readiness
from video_bundle_agent.bundle.writer import write_json

ARTIFACT_PURPOSES: dict[str, str] = {
    "metadata_path": "source metadata",
    "transcript_path": "timed transcript segments",
    "transcript_text_path": "plain transcript text",
    "transcript_alternatives_path": "alternative transcript references",
    "transcript_comparison_path": "primary vs alternative transcript comparison",
    "comments_path": "bounded source comments",
    "danmaku_path": "danmaku evidence",
    "audience_feedback_path": "lightweight audience feedback",
    "source_chapters_path": "original platform chapters",
    "slides_path": "screenshot and keyframe evidence",
    "content_profile_path": "Codex-authored content type and visual policy",
    "diagnostics_path": "tool and provider diagnostics",
    "manifest_path": "bundle file manifest",
}

COMMENT_BUCKETS: tuple[tuple[str, str], ...] = (
    ("top_liked", "top liked comments"),
    ("top_replied", "most replied comments"),
    ("question_comments", "audience questions"),
    ("critical_comments", "critical comments"),
    ("supportive_comments", "supportive comments"),
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _read_bundle_artifact(bundle_dir: Path, bundle: dict[str, Any], field: str) -> dict[str, Any]:
    relative_path = bundle.get(field)
    if not relative_path:
        return {}
    return _read_json_if_exists(bundle_dir / str(relative_path))


def _clip(value: Any, *, limit: int = 360) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _format_timestamp(seconds: Any) -> str:
    try:
        total_seconds = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return "00:00"
    minutes, second = divmod(total_seconds, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minute:02d}:{second:02d}"
    return f"{minute:02d}:{second:02d}"


def _metadata_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    if not metadata:
        return {"available": False}
    return {
        "available": True,
        "title": metadata.get("title") or "",
        "description_excerpt": _clip(metadata.get("description"), limit=500),
        "duration": metadata.get("duration"),
        "published_at": metadata.get("published_at"),
        "uploader": metadata.get("uploader") or metadata.get("channel") or "",
        "channel": metadata.get("channel") or "",
        "view_count": metadata.get("view_count"),
        "like_count": metadata.get("like_count"),
        "comment_count": metadata.get("comment_count"),
        "thumbnail": metadata.get("thumbnail") or "",
        "tags": metadata.get("tags") or [],
        "categories": metadata.get("categories") or [],
    }


def _transcript_summary(
    bundle_dir: Path,
    bundle: dict[str, Any],
    transcript: dict[str, Any],
) -> dict[str, Any]:
    segments = transcript.get("segments") or []
    sample_segments = [
        {
            "start": segment.get("start"),
            "end": segment.get("end"),
            "text": _clip(segment.get("text"), limit=220),
        }
        for segment in segments[:5]
        if isinstance(segment, dict)
    ]
    text_path = bundle.get("transcript_text_path")
    return {
        "available": bool(segments),
        "path": bundle.get("transcript_path"),
        "text_path": text_path if text_path and (bundle_dir / str(text_path)).exists() else None,
        "transcript_source": transcript.get("transcript_source"),
        "language": transcript.get("language"),
        "segment_count": len(segments),
        "sample_segments": sample_segments,
    }


def _compact_comparison_window(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "start": item.get("start"),
        "end": item.get("end"),
        "time": _format_timestamp(item.get("start")),
        "similarity": item.get("similarity"),
        "term_differences": item.get("term_differences") or {},
        "word_differences": item.get("word_differences") or {},
        "primary_text": _clip(item.get("primary_text"), limit=300),
        "alternative_text": _clip(item.get("alternative_text"), limit=300),
    }


def _transcript_comparison_summary(
    bundle_dir: Path,
    bundle: dict[str, Any],
    *,
    max_flagged_windows: int = 8,
) -> dict[str, Any]:
    path = bundle.get("transcript_comparison_path")
    if not path or not (bundle_dir / str(path)).exists():
        return {"available": False, "path": path}
    payload = _read_json(bundle_dir / str(path))
    items = [item for item in payload.get("items") or [] if isinstance(item, dict)]
    flagged = [item for item in items if item.get("flagged")]
    comparison = payload.get("comparison") or {}
    return {
        "available": True,
        "path": path,
        "primary": payload.get("primary") or {},
        "alternative": payload.get("alternative") or {},
        "window_count": comparison.get("window_count", len(items)),
        "flagged_window_count": comparison.get("flagged_window_count", len(flagged)),
        "flagged_windows": [
            _compact_comparison_window(item) for item in flagged[:max_flagged_windows]
        ],
        "usage_note": (
            "Flagged windows are review targets, not final accuracy judgments. "
            "Codex should inspect both transcript versions before trusting disputed terms."
        ),
    }


def _compact_comment(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id") or "",
        "author_name": item.get("author_name") or "",
        "text": _clip(item.get("text"), limit=260),
        "like_count": item.get("like_count"),
        "reply_count": item.get("reply_count"),
        "published_at": item.get("published_at") or "",
    }


def _audience_feedback_summary(
    bundle: dict[str, Any],
    feedback: dict[str, Any],
) -> dict[str, Any]:
    if not feedback:
        return {"available": False, "path": bundle.get("audience_feedback_path")}
    stats = feedback.get("stats") or {}
    buckets: list[dict[str, Any]] = []
    for key, label in COMMENT_BUCKETS:
        items = [item for item in stats.get(key) or [] if isinstance(item, dict)]
        buckets.append(
            {
                "key": key,
                "label": label,
                "count": len(items),
                "items": [_compact_comment(item) for item in items[:3]],
            }
        )
    return {
        "available": True,
        "path": bundle.get("audience_feedback_path"),
        "has_comments": feedback.get("has_comments"),
        "count_fetched": feedback.get("count_fetched"),
        "signals": feedback.get("signals") or {},
        "buckets": buckets,
    }


def _evidence_files(bundle: dict[str, Any]) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for field, purpose in ARTIFACT_PURPOSES.items():
        path = bundle.get(field)
        if path:
            files.append({"path": str(path), "purpose": purpose})
    return files


def _source_chapters_summary(bundle_dir: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    chapters = _read_bundle_artifact(bundle_dir, bundle, "source_chapters_path")
    if not chapters:
        fallback = _read_json_if_exists(bundle_dir / "source_chapters.json")
        chapters = fallback if isinstance(fallback, dict) else {}
    items = [item for item in chapters.get("items") or [] if isinstance(item, dict)]
    return {
        "available": bool(items),
        "path": bundle.get("source_chapters_path") or (
            "source_chapters.json" if (bundle_dir / "source_chapters.json").exists() else None
        ),
        "source": chapters.get("chapter_source") or chapters.get("source_name") or "",
        "count": len(items),
        "items": [
            {
                "id": item.get("id") or f"chapter_{index:04d}",
                "title": _clip(item.get("title") or item.get("content"), limit=120),
                "start": item.get("start"),
                "end": item.get("end"),
                "time": item.get("time")
                or (
                    f"{_format_timestamp(item.get('start'))}-{_format_timestamp(item.get('end'))}"
                    if item.get("end") is not None
                    else _format_timestamp(item.get("start"))
                ),
                "summary": _clip(item.get("summary") or item.get("title"), limit=240),
            }
            for index, item in enumerate(items, start=1)
        ],
    }


def _diagnostic_records(bundle_dir: Path, bundle: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = _read_bundle_artifact(bundle_dir, bundle, "diagnostics_path")
    return [record for record in diagnostics.get("records") or [] if isinstance(record, dict)]


def _limitations(
    *,
    readiness: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    bundle: dict[str, Any],
    comparison: dict[str, Any],
) -> list[str]:
    limitations: list[str] = []
    for blocker in readiness.get("blockers") or []:
        message = blocker.get("message") or blocker.get("code")
        if message:
            limitations.append(f"Blocker: {message}")
    for warning in readiness.get("warnings") or []:
        message = warning.get("message") or warning.get("code")
        if message:
            limitations.append(f"Warning: {message}")
    for record in diagnostics:
        severity = record.get("severity")
        if severity not in {"warning", "error"}:
            continue
        code = record.get("code") or severity.upper()
        message = record.get("message") or ""
        limitations.append(f"{severity}: {code} {message}".strip())
    capabilities = bundle.get("capabilities") or {}
    if not capabilities.get("has_ocr"):
        limitations.append(
            "OCR text is unavailable in this phase; visual claims need screenshot review."
        )
    if comparison.get("available") and comparison.get("flagged_window_count"):
        limitations.append(
            "Some automatic subtitle windows differ from the local transcription comparison."
        )
    return list(dict.fromkeys(limitations))


def _transcript_excerpt(window: list[dict[str, Any]], *, limit: int = 260) -> str:
    text = " ".join(
        str(segment.get("text") or "") for segment in window if isinstance(segment, dict)
    )
    return _clip(text, limit=limit)


def _comparison_excerpt(windows: list[dict[str, Any]]) -> str:
    if not windows:
        return ""
    first = windows[0]
    terms = first.get("term_differences") or {}
    primary_terms = ", ".join(map(str, terms.get("primary_only") or []))
    alternative_terms = ", ".join(map(str, terms.get("alternative_only") or []))
    if primary_terms or alternative_terms:
        return (
            f"Transcript check: primary only [{primary_terms}], "
            f"alternative only [{alternative_terms}]."
        )
    return "Transcript check: this nearby window was flagged for subtitle/transcription mismatch."


def _draft_metrics(metadata: dict[str, Any], audience: dict[str, Any]) -> list[dict[str, str]]:
    metrics: list[dict[str, str]] = []
    if metadata.get("duration") is not None:
        metrics.append({"label": "duration", "value": _format_timestamp(metadata.get("duration"))})
    if metadata.get("view_count") is not None:
        metrics.append({"label": "views", "value": str(metadata["view_count"])})
    if metadata.get("like_count") is not None:
        metrics.append({"label": "likes", "value": str(metadata["like_count"])})
    count = audience.get("count_fetched")
    if count is not None:
        metrics.append({"label": "comment samples", "value": str(count)})
    return metrics[:4]


def _draft_feedback(audience: dict[str, Any]) -> list[dict[str, Any]]:
    if not audience.get("available"):
        return [{"title": "Audience feedback unavailable", "body": ["Comments were not fetched."]}]
    cards: list[dict[str, Any]] = []
    for bucket in audience.get("buckets") or []:
        items = bucket.get("items") or []
        if not items:
            continue
        body = [f"{item.get('author_name')}: {item.get('text')}" for item in items]
        cards.append({"title": bucket.get("label") or bucket.get("key"), "body": body})
    return cards or [{"title": "Audience feedback", "body": ["No notable comment buckets."]}]


def _build_draft_content(report_input: dict[str, Any]) -> dict[str, Any]:
    metadata = report_input.get("metadata") or {}
    source = report_input.get("source") or {}
    profile = report_input.get("content_profile") or {}
    selected = report_input.get("selected_evidence") or {}
    audience = report_input.get("audience_feedback") or {}
    comparison = report_input.get("transcript_comparison") or {}
    source_chapters = report_input.get("source_chapters") or {}
    evidence_files = report_input.get("evidence_files") or []
    limitations = report_input.get("limitations") or []

    title = metadata.get("title") or "Video report draft"
    primary_type = profile.get("primary_type") or "unclassified video"
    tags = list(profile.get("type_tags") or [])
    if not tags:
        tags = [str(source.get("platform") or "video"), "evidence draft"]

    visual_evidence: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    for index, item in enumerate(selected.get("selected_images") or [], start=1):
        transcript_excerpt = _transcript_excerpt(item.get("transcript_window") or [])
        comparison_excerpt = _comparison_excerpt(item.get("transcript_comparison_windows") or [])
        caption_parts = [part for part in (transcript_excerpt, comparison_excerpt) if part]
        caption = " ".join(caption_parts) or "Codex should inspect this screenshot before writing."
        time_label = _format_timestamp(item.get("timestamp"))
        visual_evidence.append(
            {
                "image_path": item.get("path"),
                "title": f"Screenshot {index:02d} · {time_label}",
                "caption": caption,
            }
        )
        timeline.append(
            {
                "time": time_label,
                "topic": f"Visual evidence {index:02d}",
                "summary": transcript_excerpt or "No nearby transcript excerpt.",
                "evidence": item.get("path") or "",
            }
        )
    if source_chapters.get("available"):
        timeline = [
            {
                "time": item.get("time") or _format_timestamp(item.get("start")),
                "topic": item.get("title") or f"Chapter {index}",
                "summary": item.get("summary") or item.get("title") or "",
                "evidence": source_chapters.get("path") or "source_chapters.json",
            }
            for index, item in enumerate(source_chapters.get("items") or [], start=1)
            if isinstance(item, dict)
        ]

    sections: list[dict[str, Any]] = [
        {
            "title": "Draft status",
            "body": [
                (
                    "This is a renderer-compatible scaffold generated from bundle evidence. "
                    "Codex must replace it with the final Chinese analysis after reading "
                    "the evidence."
                )
            ],
        }
    ]
    flagged = comparison.get("flagged_windows") or []
    if flagged:
        sections.append(
            {
                "title": "Transcript review targets",
                "body": [
                    (
                        f"{item.get('time')}: primary=\"{item.get('primary_text')}\"; "
                        f"alternative=\"{item.get('alternative_text')}\""
                    )
                    for item in flagged[:4]
                ],
            }
        )

    return {
        "title": title,
        "eyebrow": f"{source.get('platform') or 'video'} · {primary_type} · evidence draft",
        "summary": (
            "This draft only organizes bundle evidence. It is not the final report."
        ),
        "conclusion": (
            "Codex should write the final conclusion from transcript and visual evidence."
        ),
        "tags": tags,
        "metrics": _draft_metrics(metadata, audience),
        "visual_evidence": visual_evidence,
        "timeline": timeline,
        "sections": sections,
        "audience_feedback": _draft_feedback(audience),
        "recommendations": ["Replace this scaffold with evidence-backed final recommendations."],
        "project_notes": [
            "Generated by video-bundle-agent prepare-report without LLM calls.",
            "Use report.input.json as the audit source for report writing.",
        ],
        "evidence_files": evidence_files,
        "limitations": limitations,
    }


def prepare_report_input(
    bundle_dir: Path,
    *,
    max_images: int = 12,
    transcript_window_seconds: float = 20,
    write: bool = True,
    draft_content: bool = True,
) -> dict[str, Any]:
    bundle_dir = bundle_dir.resolve()
    bundle = _read_json_if_exists(bundle_dir / "bundle.json")
    readiness = evaluate_bundle_readiness(bundle_dir)
    selected = select_report_evidence(
        bundle_dir,
        max_images=max_images,
        transcript_window_seconds=transcript_window_seconds,
    )

    metadata_raw = _read_bundle_artifact(bundle_dir, bundle, "metadata_path")
    transcript_raw = _read_bundle_artifact(bundle_dir, bundle, "transcript_path")
    feedback_raw = _read_bundle_artifact(bundle_dir, bundle, "audience_feedback_path")
    content_profile = _read_bundle_artifact(bundle_dir, bundle, "content_profile_path")
    if not content_profile:
        content_profile = _read_json_if_exists(bundle_dir / "content_profile.json")

    diagnostics = _diagnostic_records(bundle_dir, bundle)
    comparison = _transcript_comparison_summary(bundle_dir, bundle)
    audience = _audience_feedback_summary(bundle, feedback_raw)
    source_chapters = _source_chapters_summary(bundle_dir, bundle)

    payload: dict[str, Any] = {
        "schema_version": "0.1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "bundle_dir": str(bundle_dir),
        "source": bundle.get("source") or {},
        "readiness": readiness,
        "metadata": _metadata_summary(metadata_raw),
        "content_profile": content_profile,
        "transcript": _transcript_summary(bundle_dir, bundle, transcript_raw),
        "transcript_comparison": comparison,
        "source_chapters": source_chapters,
        "audience_feedback": audience,
        "selected_evidence": selected,
        "evidence_files": _evidence_files(bundle),
        "limitations": _limitations(
            readiness=readiness,
            diagnostics=diagnostics,
            bundle=bundle,
            comparison=comparison,
        ),
        "report_contract": {
            "input_path": "report.input.json",
            "draft_content_path": "report.content.draft.json",
            "report_output_contract_path": "docs/report-output-contract.md",
            "default_mode": "quick",
            "mode_triggers": {
                "deep": ["深入分析", "深度报告", "详细解读", "deep 模式"],
            },
            "evaluation": {
                "scale": {"min": 1, "max": 5},
                "placement": {
                    "snapshot": "first_content_module_before_video_overview",
                    "reasoning": "later_codex_critique_section",
                },
                "dimensions": [
                    {"key": "credibility", "label": "可信度"},
                    {"key": "originality", "label": "原创性"},
                    {"key": "value_density", "label": "价值密度"},
                    {"key": "argument_strength", "label": "论证强度"},
                    {"key": "information_density", "label": "信息密度"},
                    {"key": "timeliness", "label": "时效性"},
                ],
            },
            "audience_feedback_rules": {
                "quick": "Summarize 2-4 main feedback directions when comments are available.",
                "deep": (
                    "Representative comment quotes are allowed; include like_count when available "
                    "and label partial samples as partial. Cited comments must trace to "
                    "comments.json."
                ),
            },
            "final_content_paths": {
                "quick": "report.content.quick.json",
                "deep": "report.content.deep.json",
            },
            "html_paths": {
                "quick": "report.zh.quick.html",
                "deep": "report.zh.deep.html",
            },
            "pdf_paths": {
                "quick": "report.zh.quick.pdf",
                "deep": "report.zh.deep.pdf",
            },
            "png_paths": {
                "quick": "report.zh.quick.png",
                "deep": "report.zh.deep.png",
            },
            "compatibility_paths": {
                "content": "report.content.json",
                "html": "report.zh.html",
                "pdf": "report.zh.pdf",
                "png": "report.zh.png",
            },
            "note": (
                "The bundle engine prepares mode-independent evidence only. "
                "Codex writes quick/deep final report content."
            ),
        },
        "generated_paths": {
            "report_input_path": None,
            "report_content_draft_path": None,
        },
    }

    if write:
        write_json(bundle_dir / "report.input.json", payload)
        payload["generated_paths"]["report_input_path"] = "report.input.json"
        if draft_content and readiness["report_ready"]:
            draft = _build_draft_content(payload)
            write_json(bundle_dir / "report.content.draft.json", draft)
            payload["generated_paths"]["report_content_draft_path"] = (
                "report.content.draft.json"
            )
            write_json(bundle_dir / "report.input.json", payload)

    return payload
