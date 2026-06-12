from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from video_bundle_agent.tools.paths import WORKSHOP_ROOT, find_executable
from video_bundle_agent.tools.process import run_command

WHISPER_CPP_MODEL_FILENAMES = (
    "ggml-large-v3-turbo.bin",
    "ggml-large-v3-turbo-q8_0.bin",
    "ggml-large-v3-turbo-q5_0.bin",
    "ggml-large-v3-turbo-q5_1.bin",
    "ggml-large-v3-turbo-q4_0.bin",
    "ggml-large-v3-turbo-q4_1.bin",
    "ggml-large-v3.bin",
    "ggml-medium.bin",
    "ggml-small.bin",
    "ggml-base.bin",
)


def whisper_cpp_model_candidates() -> list[Path]:
    env_candidates = [
        os.environ.get("VIDEO_BUNDLE_AGENT_WHISPER_MODEL"),
        os.environ.get("WHISPER_MODEL"),
    ]
    candidates = [Path(value) for value in env_candidates if value]
    model_dirs = [
        WORKSHOP_ROOT / "whisper.cpp" / "models",
        WORKSHOP_ROOT / "whisper.cpp" / "v1.8.6" / "models",
    ]
    candidates.extend(
        model_dir / filename
        for model_dir in model_dirs
        for filename in WHISPER_CPP_MODEL_FILENAMES
    )
    return candidates


def whisper_cpp_model_path() -> Path | None:
    for candidate in whisper_cpp_model_candidates():
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _parse_timestamp(value: str) -> float:
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


def _seconds_from_whisper_segment(segment: dict[str, Any], key: str) -> float:
    offsets = segment.get("offsets") or {}
    if key in offsets:
        return float(offsets[key]) / 1000
    timestamps = segment.get("timestamps") or {}
    if key in timestamps:
        return _parse_timestamp(str(timestamps[key]))
    return 0.0


def parse_whisper_cpp_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_segments = data.get("transcription") or data.get("segments") or []
    segments: list[dict[str, Any]] = []
    for index, segment in enumerate(raw_segments):
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        start = _seconds_from_whisper_segment(segment, "from")
        end = _seconds_from_whisper_segment(segment, "to")
        segments.append(
            {
                "id": str(index),
                "start": start,
                "end": end,
                "duration": max(0.0, end - start),
                "text": text,
                "source": "whisper_cpp",
            }
        )
    return segments


def build_transcript_payload(
    *,
    source: dict[str, Any],
    segments: list[dict[str, Any]],
    language: str,
    transcript_source: str,
    model_path: Path | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "fetched_at": datetime.now(UTC).isoformat(),
        "language": language,
        "transcript_source": transcript_source,
        "model_path": str(model_path) if model_path else None,
        "segments": segments,
    }


def whisper_output_path(output_base: Path, extension: str) -> Path:
    return Path(f"{output_base}{extension}")


def transcribe_with_whisper_cpp(
    audio_path: Path,
    output_dir: Path,
    *,
    language: str = "auto",
    timeout_seconds: int = 7200,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    whisper = find_executable("whisper")
    if not whisper:
        raise FileNotFoundError("whisper.cpp CLI was not found")
    model_path = whisper_cpp_model_path()
    if not model_path:
        raise FileNotFoundError("whisper.cpp model file was not found")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_base = output_dir / audio_path.stem
    run_command(
        [
            whisper,
            "-m",
            model_path,
            "-f",
            audio_path,
            "-l",
            language,
            "-oj",
            "-of",
            output_base,
            "-np",
        ],
        timeout_seconds=timeout_seconds,
    )
    json_path = whisper_output_path(output_base, ".json")
    if not json_path.exists():
        raise FileNotFoundError("whisper.cpp did not produce a JSON transcript")
    return (
        {
            "engine": "whisper_cpp",
            "model_path": model_path,
            "raw_json_path": json_path,
            "language": language,
        },
        parse_whisper_cpp_json(json_path),
    )
