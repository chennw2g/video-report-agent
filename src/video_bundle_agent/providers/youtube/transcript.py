from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any


def parse_timestamp(value: str) -> float:
    hours = 0
    parts = value.replace(",", ".").split(":")
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    elif len(parts) == 2:
        minutes = int(parts[0])
        seconds = float(parts[1])
    else:
        minutes = 0
        seconds = float(parts[0])
    return hours * 3600 + minutes * 60 + seconds


def parse_json3(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    segments: list[dict[str, Any]] = []
    for index, event in enumerate(data.get("events", [])):
        text = "".join(seg.get("utf8", "") for seg in event.get("segs", []))
        text = re.sub(r"\s+", " ", unescape(text)).strip()
        if not text:
            continue
        start = float(event.get("tStartMs", 0)) / 1000
        duration = float(event.get("dDurationMs", 0)) / 1000
        segments.append(
            {
                "id": str(index),
                "start": start,
                "end": start + duration if duration else start,
                "duration": duration,
                "text": text,
                "source": "yt_dlp_subtitle",
            }
        )
    return segments


def parse_vtt(path: Path) -> list[dict[str, Any]]:
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8"))
    segments: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        start_text, end_text = [
            part.strip().split()[0] for part in lines[timing_index].split("-->")
        ]
        text = " ".join(lines[timing_index + 1 :])
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", unescape(text)).strip()
        if not text:
            continue
        start = parse_timestamp(start_text)
        end = parse_timestamp(end_text)
        segments.append(
            {
                "id": str(len(segments)),
                "start": start,
                "end": end,
                "duration": max(0.0, end - start),
                "text": text,
                "source": "yt_dlp_subtitle",
            }
        )
    return segments


def select_subtitle_file(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    ordered = sorted(paths, key=lambda path: path.name.lower())
    priorities = (
        ".en.",
        ".zh-hans.",
        ".zh-hant.",
        ".zh.",
    )
    for priority in priorities:
        for path in ordered:
            if priority in path.name.lower():
                return path
    return ordered[0]


def parse_subtitle(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json3":
        return parse_json3(path)
    if path.suffix.lower() == ".vtt":
        return parse_vtt(path)
    return []
