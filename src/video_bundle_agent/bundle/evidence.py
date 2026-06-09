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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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

    keyword_limit = max(1, max_images // 2)
    keyword_indexes = _keyword_slide_indexes(
        segments=segments,
        slides=slides,
        limit=keyword_limit,
    )
    uniform_indexes = _uniform_slide_indexes(len(slides), max_images)
    selected_indexes = _dedupe_preserve_order(keyword_indexes + uniform_indexes, max_images)

    selected_images: list[dict[str, Any]] = []
    for index in selected_indexes:
        slide = slides[index]
        timestamp = _slide_timestamp(slide)
        path = slide.get("path")
        selected_images.append(
            {
                "id": slide.get("id") or f"slide_{index + 1:04d}",
                "timestamp": timestamp,
                "path": path,
                "absolute_path": str(bundle_dir / path) if path else None,
                "selection_reasons": [
                    "keyword_nearby" if index in keyword_indexes else "timeline_coverage"
                ],
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
        },
        "selected_images": selected_images,
    }
