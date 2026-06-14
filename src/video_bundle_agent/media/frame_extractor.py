from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from video_bundle_agent.tools.paths import find_executable
from video_bundle_agent.tools.process import run_command

VisualRecallLevel = Literal["low", "medium", "high"]

VISUAL_RECALL_INTERVALS: dict[VisualRecallLevel, int] = {
    "low": 15,
    "medium": 5,
    "high": 2,
}

KEYWORD_TRIGGER_TERMS = (
    "here",
    "look",
    "click",
    "setting",
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
    "important",
    "chart",
    "screen",
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
    "dividend",
    "preferred",
    "financing",
    "debt",
    "bitcoin",
    "market",
    "cash",
    "loss",
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

SCENE_TIME_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")


@dataclass
class FrameCandidate:
    timestamp: float
    source_reasons: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


def interval_for_visual_recall(level: str) -> int:
    if level not in VISUAL_RECALL_INTERVALS:
        raise ValueError(f"Unsupported visual recall level: {level}")
    return VISUAL_RECALL_INTERVALS[level]  # type: ignore[index]


def format_timestamp_filename(seconds: float, reason: str = "fixed") -> str:
    return f"{seconds:08.1f}s_{reason}.png"


def _normalized_timestamp(seconds: float) -> float:
    return round(max(0.0, seconds), 1)


def _clamped_timestamp(seconds: float, duration: float) -> float:
    if duration <= 0:
        return _normalized_timestamp(seconds)
    return _normalized_timestamp(min(max(0.0, seconds), max(0.0, duration - 0.1)))


def fixed_interval_timestamps(
    *,
    duration: float,
    interval_seconds: int,
    max_screenshots: int,
) -> tuple[list[float], bool, int]:
    if duration <= 0 or interval_seconds <= 0:
        return [], False, 0

    last_timestamp = max(0.0, duration - 0.1)
    timestamps: list[float] = []
    current = 0.0
    while current < duration and current <= last_timestamp:
        timestamps.append(round(current, 1))
        current += interval_seconds
    if not timestamps:
        timestamps = [0.0]

    original_count = len(timestamps)
    if max_screenshots <= 0 or original_count <= max_screenshots:
        return timestamps, False, 0
    if max_screenshots == 1:
        return [0.0], True, original_count - 1

    step = last_timestamp / (max_screenshots - 1)
    sampled = [round(min(last_timestamp, index * step), 1) for index in range(max_screenshots)]
    return sampled, True, original_count - len(sampled)


def fixed_interval_candidates(
    *,
    duration: float,
    interval_seconds: int,
    max_screenshots: int,
) -> tuple[list[FrameCandidate], bool, int]:
    timestamps, sampled_due_to_cap, skipped_count = fixed_interval_timestamps(
        duration=duration,
        interval_seconds=interval_seconds,
        max_screenshots=max_screenshots,
    )
    return (
        [
            FrameCandidate(
                timestamp=timestamp,
                source_reasons=["fixed_interval"],
            )
            for timestamp in timestamps
        ],
        sampled_due_to_cap,
        skipped_count,
    )


def _ascii_term_matches(text: str, term: str) -> bool:
    if " " in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def keyword_matches(text: str, terms: tuple[str, ...] = KEYWORD_TRIGGER_TERMS) -> list[str]:
    lower_text = text.lower()
    matches: list[str] = []
    for term in terms:
        lower_term = term.lower()
        if lower_term.isascii() and re.fullmatch(r"[a-z0-9]+", lower_term):
            matched = _ascii_term_matches(lower_text, lower_term)
        else:
            matched = lower_term in lower_text
        if matched:
            matches.append(term)
    return matches


def keyword_trigger_candidates(
    *,
    segments: list[dict[str, Any]],
    duration: float,
    max_candidates: int,
    offsets_seconds: tuple[float, ...] = (-2.0, 0.0, 2.0),
    min_gap_seconds: float = 1.0,
) -> tuple[list[FrameCandidate], int]:
    if max_candidates <= 0:
        return [], 0

    candidates: list[FrameCandidate] = []
    matched_segment_count = 0
    for segment in segments:
        text = str(segment.get("text") or "")
        matches = keyword_matches(text)
        if not matches:
            continue
        matched_segment_count += 1
        start = float(segment.get("start") or 0)
        for offset in offsets_seconds:
            timestamp = _clamped_timestamp(start + offset, duration)
            if any(
                abs(candidate.timestamp - timestamp) < min_gap_seconds
                for candidate in candidates
            ):
                continue
            candidates.append(
                FrameCandidate(
                    timestamp=timestamp,
                    source_reasons=["keyword_trigger"],
                    metadata={
                        "keyword_matches": matches[:5],
                        "trigger_segment_start": start,
                        "trigger_text": text,
                    },
                )
            )
            if len(candidates) >= max_candidates:
                skipped = max(0, matched_segment_count - len(candidates))
                return candidates, skipped
    return candidates, 0


def parse_scene_change_timestamps(
    ffmpeg_output: str,
    *,
    max_scenes: int,
    min_gap_seconds: float,
    duration: float | None = None,
) -> list[float]:
    timestamps: list[float] = []
    for match in SCENE_TIME_RE.finditer(ffmpeg_output):
        timestamp = float(match.group(1))
        if duration is not None and timestamp >= duration:
            continue
        timestamp = _normalized_timestamp(timestamp)
        if timestamps and timestamp - timestamps[-1] < min_gap_seconds:
            continue
        timestamps.append(timestamp)
        if len(timestamps) >= max_scenes:
            break
    return timestamps


def detect_scene_change_timestamps(
    *,
    video_path: Path,
    threshold: float = 0.35,
    max_scenes: int = 80,
    min_gap_seconds: float = 4.0,
    duration: float | None = None,
    timeout_seconds: int = 900,
) -> list[float]:
    ffmpeg = find_executable("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg was not found")
    completed = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "info",
            "-i",
            video_path,
            "-vf",
            f"select='gt(scene,{threshold})',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ],
        timeout_seconds=timeout_seconds,
    )
    return parse_scene_change_timestamps(
        completed.stderr + "\n" + completed.stdout,
        max_scenes=max_scenes,
        min_gap_seconds=min_gap_seconds,
        duration=duration,
    )


def scene_change_candidates(
    *,
    timestamps: list[float],
) -> list[FrameCandidate]:
    return [
        FrameCandidate(
            timestamp=_normalized_timestamp(timestamp),
            source_reasons=["scene_change"],
        )
        for timestamp in timestamps
    ]


def _merge_metadata(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if key == "keyword_matches":
            values = list(merged.get(key) or [])
            for item in value or []:
                if item not in values:
                    values.append(item)
            merged[key] = values
        elif key == "trigger_text":
            values = list(merged.get("trigger_texts") or [])
            if value and value not in values:
                values.append(value)
            merged["trigger_texts"] = values
        elif key not in merged:
            merged[key] = value
    return merged


def merge_frame_candidates(candidates: list[FrameCandidate]) -> list[FrameCandidate]:
    by_timestamp: dict[float, FrameCandidate] = {}
    for candidate in candidates:
        timestamp = _normalized_timestamp(candidate.timestamp)
        existing = by_timestamp.get(timestamp)
        if not existing:
            by_timestamp[timestamp] = FrameCandidate(
                timestamp=timestamp,
                source_reasons=list(candidate.source_reasons),
                metadata=dict(candidate.metadata),
            )
            continue
        for reason in candidate.source_reasons:
            if reason not in existing.source_reasons:
                existing.source_reasons.append(reason)
        existing.metadata = _merge_metadata(existing.metadata, candidate.metadata)
    return sorted(by_timestamp.values(), key=lambda item: item.timestamp)


def _even_sample(items: list[FrameCandidate], limit: int) -> list[FrameCandidate]:
    if limit <= 0 or not items:
        return []
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[0]]
    step = (len(items) - 1) / (limit - 1)
    return [items[round(index * step)] for index in range(limit)]


def apply_candidate_cap(
    candidates: list[FrameCandidate],
    *,
    max_candidates: int,
) -> tuple[list[FrameCandidate], int]:
    merged = merge_frame_candidates(candidates)
    if max_candidates <= 0:
        return merged, 0
    if len(merged) <= max_candidates:
        return merged, 0

    focus = [
        candidate
        for candidate in merged
        if any(reason != "fixed_interval" for reason in candidate.source_reasons)
    ]
    focus_limit = min(len(focus), max(1, max_candidates // 2))
    selected = _even_sample(focus, focus_limit)
    selected_timestamps = {candidate.timestamp for candidate in selected}
    remaining = [
        candidate for candidate in merged if candidate.timestamp not in selected_timestamps
    ]
    selected.extend(_even_sample(remaining, max_candidates - len(selected)))
    capped = sorted(merge_frame_candidates(selected), key=lambda item: item.timestamp)
    return capped, len(merged) - len(capped)


def _filename_reason(source_reasons: list[str]) -> str:
    if "fixed_interval" in source_reasons:
        return "fixed"
    if "semantic_anchor" in source_reasons:
        return "anchor"
    if "scene_change" in source_reasons:
        return "scene"
    if "keyword_trigger" in source_reasons:
        return "keyword"
    return "frame"


def extract_frame(
    *,
    video_path: Path,
    output_path: Path,
    timestamp: float,
    timeout_seconds: int = 120,
) -> Path:
    ffmpeg = find_executable("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg was not found")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-q:v",
            "1",
            output_path,
        ],
        timeout_seconds=timeout_seconds,
    )
    return output_path


def extracted_frame_item(
    *,
    slide_id: str,
    candidate: FrameCandidate,
    path: Path,
) -> dict[str, object]:
    item: dict[str, object] = {
        "id": slide_id,
        "timestamp": candidate.timestamp,
        "path": path,
        "source_reasons": candidate.source_reasons,
        "ocr_text": "",
        "ocr_confidence": None,
        "sharpness": None,
        "brightness": None,
        "similarity_hash": None,
        "selected": False,
    }
    item.update(candidate.metadata)
    return item


def extract_frame_candidates(
    *,
    video_path: Path,
    output_dir: Path,
    candidates: list[FrameCandidate],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for index, candidate in enumerate(merge_frame_candidates(candidates), start=1):
        reason = _filename_reason(candidate.source_reasons)
        filename = format_timestamp_filename(candidate.timestamp, reason)
        output_path = output_dir / filename
        extract_frame(video_path=video_path, output_path=output_path, timestamp=candidate.timestamp)
        items.append(
            extracted_frame_item(
                slide_id=f"slide_{index:04d}",
                candidate=candidate,
                path=output_path,
            )
        )
    return items


def extract_fixed_interval_frames(
    *,
    video_path: Path,
    output_dir: Path,
    timestamps: list[float],
) -> list[dict[str, object]]:
    return extract_frame_candidates(
        video_path=video_path,
        output_dir=output_dir,
        candidates=[
            FrameCandidate(timestamp=timestamp, source_reasons=["fixed_interval"])
            for timestamp in timestamps
        ],
    )
