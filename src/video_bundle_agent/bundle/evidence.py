from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from video_bundle_agent.bundle.readiness import evaluate_bundle_readiness
from video_bundle_agent.media.frame_extractor import KEYWORD_TRIGGER_TERMS

FOCUS_TERMS = (
    "here",
    "look",
    "click",
    "settings",
    "error",
    "result",
    "data",
    "risk",
    "compare",
    "first step",
    "second step",
    "next",
    "attention",
    "key",
    "valuation",
    "pe",
    "pb",
    "roe",
    "profit",
    "revenue",
    "cash flow",
    "drawdown",
    "position",
    "buy",
    "sell",
    "support",
    "resistance",
    "earnings",
    "这里",
    "看这里",
    "点击",
    "设置",
    "报错",
    "结果",
    "数据",
    "风险",
    "对比",
    "第一步",
    "第二步",
    "接下来",
    "注意",
    "关键",
    "估值",
    "利润",
    "营收",
    "现金流",
    "涨幅",
    "跌幅",
    "回撤",
    "仓位",
    "买入",
    "卖出",
    "支撑位",
    "压力位",
    "财报",
)

FOCUS_TERMS = KEYWORD_TRIGGER_TERMS
DEFAULT_BODY_SCREENSHOT_POLICY = "selective"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(bundle_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(bundle_dir.resolve()).as_posix()
    except ValueError:
        return str(path)


def _resolve_plan_path(bundle_dir: Path, plan_path: Path | None) -> Path | None:
    if plan_path is None:
        candidate = bundle_dir / "visual_selection_plan.json"
        return candidate if candidate.exists() else None
    if plan_path.is_absolute():
        return plan_path
    candidate = bundle_dir / plan_path
    if candidate.exists():
        return candidate
    return plan_path


def _compact_terms(values: Any, *, limit: int = 16) -> list[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split())
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        terms.append(text)
        if len(terms) >= limit:
            break
    return terms


def _anchor_terms(anchor: dict[str, Any]) -> list[str]:
    terms = _compact_terms(anchor.get("terms"))
    keywords = _compact_terms(anchor.get("keywords"))
    return _compact_terms([*terms, *keywords])


def _time_to_seconds(value: Any) -> float | None:
    text = str(value or "").strip().lower().replace("：", ":")
    if not text:
        return None
    if text.endswith("s"):
        text = text[:-1].strip()
    if ":" not in text:
        try:
            return max(0.0, float(text))
        except ValueError:
            return None
    parts = text.split(":")
    if not 1 <= len(parts) <= 3:
        return None
    try:
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
    except ValueError:
        return None
    return max(0.0, seconds)


def _parse_time_hint(value: Any) -> tuple[float, float] | None:
    text = str(value or "").strip()
    if not text:
        return None
    separators = ("-", "–", "—", "~", "至")
    for separator in separators:
        if separator not in text:
            continue
        start_text, end_text = text.split(separator, 1)
        start = _time_to_seconds(start_text)
        end = _time_to_seconds(end_text)
        if start is None or end is None:
            return None
        return (min(start, end), max(start, end))
    second = _time_to_seconds(text)
    if second is None:
        return None
    return (second, second)


def _segment_overlaps_time_hint(segment: dict[str, Any], start: float, end: float) -> bool:
    segment_start = _segment_start(segment)
    try:
        segment_end = float(segment.get("end") or segment_start)
    except (TypeError, ValueError):
        segment_end = segment_start
    return segment_end >= start and segment_start <= end


def _load_visual_selection_plan(
    bundle_dir: Path,
    plan_path: Path | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    resolved_path = _resolve_plan_path(bundle_dir, plan_path)
    if resolved_path is None:
        return None, {
            "available": False,
            "body_screenshot_policy": DEFAULT_BODY_SCREENSHOT_POLICY,
        }
    display_path = _display_path(bundle_dir, resolved_path)
    if not resolved_path.exists():
        return None, {
            "available": False,
            "path": display_path,
            "body_screenshot_policy": DEFAULT_BODY_SCREENSHOT_POLICY,
            "load_error": "visual selection plan not found",
        }
    try:
        plan = _read_json(resolved_path)
    except (OSError, json.JSONDecodeError) as exc:
        return None, {
            "available": False,
            "path": display_path,
            "body_screenshot_policy": DEFAULT_BODY_SCREENSHOT_POLICY,
            "load_error": str(exc),
        }
    anchors = [item for item in plan.get("semantic_anchors") or [] if isinstance(item, dict)]
    body_policy = str(plan.get("body_screenshot_policy") or DEFAULT_BODY_SCREENSHOT_POLICY)
    compact_anchors = []
    for index, anchor in enumerate(anchors, start=1):
        compact_anchors.append(
            {
                "id": anchor.get("id") or f"anchor_{index:04d}",
                "label": anchor.get("label") or anchor.get("title") or "",
                "terms": _anchor_terms(anchor),
                "time_hints": _compact_terms(anchor.get("time_hints"), limit=8),
                "need_screenshot": anchor.get("need_screenshot", True) is not False,
                "reason": anchor.get("reason") or "",
                "body_placement": anchor.get("body_placement") or anchor.get("placement") or "",
            }
        )
    return plan, {
        "available": True,
        "path": display_path,
        "schema_version": plan.get("schema_version"),
        "source_type": plan.get("source_type") or plan.get("primary_type") or "",
        "visual_density": plan.get("visual_density") or "",
        "body_screenshot_policy": body_policy,
        "semantic_anchor_count": len(anchors),
        "semantic_anchors": compact_anchors,
    }


def _load_bundle_inputs(bundle_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    bundle = _read_json(bundle_dir / "bundle.json")
    transcript = _read_json(bundle_dir / bundle["transcript_path"])
    slides = _read_json(bundle_dir / bundle["slides_path"])
    return bundle, transcript, slides


def _segment_text(segment: dict[str, Any]) -> str:
    return str(segment.get("text") or "")


def _segment_start(segment: dict[str, Any]) -> float:
    return float(segment.get("start") or 0)


def _slide_timestamp(slide: dict[str, Any]) -> float:
    return float(slide.get("timestamp") or 0)


def _nearest_slide_index(slides: list[dict[str, Any]], timestamp: float) -> int | None:
    if not slides:
        return None
    return min(
        range(len(slides)),
        key=lambda index: abs(_slide_timestamp(slides[index]) - timestamp),
    )


def _keyword_slide_indexes(
    *,
    segments: list[dict[str, Any]],
    slides: list[dict[str, Any]],
    limit: int,
) -> list[int]:
    indexes: list[int] = []
    seen: set[int] = set()
    lower_terms = tuple(term.lower() for term in FOCUS_TERMS)
    for segment in segments:
        text = _segment_text(segment).lower()
        if not text or not any(term in text for term in lower_terms):
            continue
        index = _nearest_slide_index(slides, _segment_start(segment))
        if index is None or index in seen:
            continue
        seen.add(index)
        indexes.append(index)
        if len(indexes) >= limit:
            break
    return indexes


def _anchor_slide_indexes(
    *,
    segments: list[dict[str, Any]],
    slides: list[dict[str, Any]],
    anchors: list[dict[str, Any]],
    limit: int,
) -> tuple[list[int], dict[int, dict[str, Any]]]:
    indexes: list[int] = []
    records: dict[int, dict[str, Any]] = {}
    seen: set[int] = set()
    if limit <= 0:
        return indexes, records

    for anchor_number, anchor in enumerate(anchors, start=1):
        if anchor.get("need_screenshot", True) is False:
            continue
        terms = _anchor_terms(anchor)
        lower_terms = [term.lower() for term in terms]
        raw_time_hints = _compact_terms(anchor.get("time_hints"), limit=8)
        parsed_hints = [
            parsed for parsed in (_parse_time_hint(item) for item in raw_time_hints) if parsed
        ]

        candidate_timestamp: float | None = None
        for segment in segments:
            text = _segment_text(segment).lower()
            term_match = bool(lower_terms) and any(term in text for term in lower_terms)
            time_match = any(
                _segment_overlaps_time_hint(segment, start, end)
                for start, end in parsed_hints
            )
            if not term_match and not time_match:
                continue
            candidate_timestamp = _segment_start(segment)
            break

        if candidate_timestamp is None and parsed_hints:
            first_start, first_end = parsed_hints[0]
            candidate_timestamp = (first_start + first_end) / 2
        if candidate_timestamp is None:
            continue

        index = _nearest_slide_index(slides, candidate_timestamp)
        if index is None or index in seen:
            continue
        seen.add(index)
        indexes.append(index)
        records[index] = {
            "anchor_id": anchor.get("id") or f"anchor_{anchor_number:04d}",
            "anchor_label": anchor.get("label") or anchor.get("title") or "",
            "anchor_reason": anchor.get("reason") or "",
            "anchor_terms": terms,
            "anchor_time_hints": raw_time_hints,
            "anchor_need_screenshot": True,
            "body_placement": anchor.get("body_placement") or anchor.get("placement") or "",
        }
        if len(indexes) >= limit:
            break
    return indexes, records


def _uniform_slide_indexes(slide_count: int, limit: int) -> list[int]:
    if slide_count <= 0 or limit <= 0:
        return []
    if slide_count <= limit:
        return list(range(slide_count))
    if limit == 1:
        return [0]
    step = (slide_count - 1) / (limit - 1)
    return [round(index * step) for index in range(limit)]


def _dedupe_preserve_order(indexes: list[int], limit: int) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for index in indexes:
        if index in seen:
            continue
        seen.add(index)
        out.append(index)
        if len(out) >= limit:
            break
    return out


def _transcript_window(
    *,
    segments: list[dict[str, Any]],
    timestamp: float,
    window_seconds: float,
) -> list[dict[str, Any]]:
    window: list[dict[str, Any]] = []
    start_min = max(0, timestamp - window_seconds)
    start_max = timestamp + window_seconds
    for segment in segments:
        start = _segment_start(segment)
        if start < start_min or start > start_max:
            continue
        window.append(
            {
                "start": start,
                "end": segment.get("end"),
                "text": _segment_text(segment),
            }
        )
    return window


def _load_transcript_comparison(bundle_dir: Path, bundle: dict[str, Any]) -> list[dict[str, Any]]:
    path = bundle.get("transcript_comparison_path")
    if not path:
        return []
    comparison_path = bundle_dir / path
    if not comparison_path.exists():
        return []
    payload = _read_json(comparison_path)
    return [item for item in payload.get("items") or [] if isinstance(item, dict)]


def _comparison_windows(
    *,
    items: list[dict[str, Any]],
    timestamp: float,
    window_seconds: float,
) -> list[dict[str, Any]]:
    start_min = max(0, timestamp - window_seconds)
    start_max = timestamp + window_seconds
    windows: list[dict[str, Any]] = []
    for item in items:
        if not item.get("flagged"):
            continue
        start = float(item.get("start") or 0)
        end = float(item.get("end") or start)
        if end < start_min or start > start_max:
            continue
        windows.append(
            {
                "start": start,
                "end": end,
                "similarity": item.get("similarity"),
                "flagged": item.get("flagged"),
                "term_differences": item.get("term_differences") or {},
                "word_differences": item.get("word_differences") or {},
                "primary_text": item.get("primary_text") or "",
                "alternative_text": item.get("alternative_text") or "",
            }
        )
    return windows


def select_report_evidence(
    bundle_dir: Path,
    *,
    max_images: int = 12,
    transcript_window_seconds: float = 20,
    plan_path: Path | None = None,
) -> dict[str, Any]:
    readiness = evaluate_bundle_readiness(bundle_dir)
    if not readiness["report_ready"]:
        return {
            "schema_version": "0.1.0",
            "bundle_dir": str(bundle_dir),
            "report_ready": False,
            "readiness": readiness,
            "selected_images": [],
        }

    bundle, transcript, slides_payload = _load_bundle_inputs(bundle_dir)
    segments = transcript.get("segments") or []
    slides = slides_payload.get("items") or []
    comparison_items = _load_transcript_comparison(bundle_dir, bundle)
    visual_plan, visual_plan_summary = _load_visual_selection_plan(bundle_dir, plan_path)
    body_screenshot_policy = (
        visual_plan_summary.get("body_screenshot_policy") or DEFAULT_BODY_SCREENSHOT_POLICY
    )

    anchors = [
        item for item in (visual_plan or {}).get("semantic_anchors") or [] if isinstance(item, dict)
    ]
    anchor_indexes, anchor_records = _anchor_slide_indexes(
        segments=segments,
        slides=slides,
        anchors=anchors,
        limit=max_images,
    )
    keyword_limit = max(1, max_images // 2)
    keyword_indexes = _keyword_slide_indexes(
        segments=segments,
        slides=slides,
        limit=keyword_limit,
    )
    uniform_indexes = _uniform_slide_indexes(len(slides), max_images)
    selected_indexes = _dedupe_preserve_order(
        anchor_indexes + keyword_indexes + uniform_indexes,
        max_images,
    )

    selected_images: list[dict[str, Any]] = []
    for index in selected_indexes:
        slide = slides[index]
        timestamp = _slide_timestamp(slide)
        path = slide.get("path")
        selection_reasons: list[str] = []
        if index in anchor_records:
            selection_reasons.append("semantic_anchor")
        if index in keyword_indexes:
            selection_reasons.append("keyword_nearby")
        if not selection_reasons:
            selection_reasons.append("timeline_coverage")
        image: dict[str, Any] = {
            "id": slide.get("id") or f"slide_{index + 1:04d}",
            "timestamp": timestamp,
            "path": path,
            "absolute_path": str(bundle_dir / path) if path else None,
            "selection_reasons": selection_reasons,
            "transcript_window": _transcript_window(
                segments=segments,
                timestamp=timestamp,
                window_seconds=transcript_window_seconds,
            ),
            "transcript_comparison_windows": _comparison_windows(
                items=comparison_items,
                timestamp=timestamp,
                window_seconds=transcript_window_seconds,
            ),
        }
        if index in anchor_records:
            image.update(anchor_records[index])
        selected_images.append(
            image
        )

    return {
        "schema_version": "0.1.0",
        "bundle_dir": str(bundle_dir),
        "report_ready": True,
        "source": bundle.get("source"),
        "readiness": readiness,
        "selection": {
            "max_images": max_images,
            "selected_count": len(selected_images),
            "slide_candidate_count": len(slides),
            "transcript_window_seconds": transcript_window_seconds,
            "selection_strategy": "plan_guided" if visual_plan else "basic",
            "body_screenshot_policy": body_screenshot_policy,
        },
        "visual_selection_plan": visual_plan_summary,
        "selected_images": selected_images,
    }
