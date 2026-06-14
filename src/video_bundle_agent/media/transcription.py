from __future__ import annotations

import json
import os
import re
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

WHISPER_CPP_LANGUAGE_MODEL_FILENAMES = (
    "ggml-base.bin",
    "ggml-small.bin",
    "ggml-medium.bin",
    "ggml-large-v3-turbo.bin",
    "ggml-large-v3.bin",
)

FUNASR_CHINESE_LANGUAGE_PREFIXES = ("zh", "cmn", "yue", "chi", "chinese")
SENSEVOICE_TAG_RE = re.compile(r"<\|[^>]+?\|>")
WHISPER_DETECTED_LANGUAGE_RE = re.compile(
    r"(?:auto-)?detected language:\s*([a-zA-Z_-]+)(?:\s*\(p\s*=\s*([0-9.]+)\))?",
    re.IGNORECASE,
)
DEFAULT_LANGUAGE_PROBE_SECONDS = 60
MIN_LANGUAGE_DETECTION_CONFIDENCE = 0.5


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


def whisper_cpp_language_model_candidates() -> list[Path]:
    env_candidates = [
        os.environ.get("VIDEO_BUNDLE_AGENT_WHISPER_LANGUAGE_MODEL"),
        os.environ.get("WHISPER_LANGUAGE_MODEL"),
    ]
    candidates = [Path(value) for value in env_candidates if value]
    model_dirs = [
        WORKSHOP_ROOT / "whisper.cpp" / "models",
        WORKSHOP_ROOT / "whisper.cpp" / "v1.8.6" / "models",
    ]
    candidates.extend(
        model_dir / filename
        for model_dir in model_dirs
        for filename in WHISPER_CPP_LANGUAGE_MODEL_FILENAMES
    )
    return candidates


def whisper_cpp_language_model_path() -> Path | None:
    for candidate in whisper_cpp_language_model_candidates():
        if candidate.exists() and candidate.is_file():
            return candidate
    return whisper_cpp_model_path()


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


def is_chinese_language(language: str | None) -> bool:
    if not language:
        return False
    normalized = language.strip().lower().replace("_", "-")
    return any(prefix in normalized for prefix in FUNASR_CHINESE_LANGUAGE_PREFIXES)


def _parse_whisper_detect_language_output(text: str) -> tuple[str | None, float | None]:
    match = WHISPER_DETECTED_LANGUAGE_RE.search(text)
    if not match:
        return None, None
    language = match.group(1).lower().replace("_", "-")
    confidence_text = match.group(2)
    confidence = float(confidence_text) if confidence_text else None
    return language, confidence


def _accept_detected_language(language: str | None, confidence: float | None) -> bool:
    if not language:
        return False
    return confidence is None or confidence >= MIN_LANGUAGE_DETECTION_CONFIDENCE


def _extract_language_probe_wav(
    audio_path: Path,
    output_dir: Path,
    *,
    duration_seconds: int = DEFAULT_LANGUAGE_PROBE_SECONDS,
) -> Path:
    ffmpeg = find_executable("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg was not found")
    output_dir.mkdir(parents=True, exist_ok=True)
    probe_path = output_dir / f"{audio_path.stem}.language_probe.wav"
    run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-t",
            str(duration_seconds),
            "-i",
            audio_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            probe_path,
        ],
        timeout_seconds=300,
    )
    return probe_path


def _serializable_language_detection(info: dict[str, Any] | None) -> dict[str, Any] | None:
    if not info:
        return None
    serialized: dict[str, Any] = {}
    for key, value in info.items():
        if isinstance(value, Path):
            serialized[key] = str(value)
        else:
            serialized[key] = value
    return serialized


def detect_language_with_whisper_cpp(
    audio_path: Path,
    output_dir: Path,
    *,
    duration_seconds: int = DEFAULT_LANGUAGE_PROBE_SECONDS,
) -> dict[str, Any]:
    whisper = find_executable("whisper")
    if not whisper:
        raise FileNotFoundError("whisper.cpp CLI was not found")
    model_path = whisper_cpp_language_model_path()
    if not model_path:
        raise FileNotFoundError("whisper.cpp language detection model file was not found")

    output_dir.mkdir(parents=True, exist_ok=True)
    probe_path = _extract_language_probe_wav(
        audio_path,
        output_dir,
        duration_seconds=duration_seconds,
    )
    completed = run_command(
        [
            whisper,
            "-m",
            model_path,
            "-f",
            probe_path,
            "-l",
            "auto",
            "-dl",
        ],
        timeout_seconds=300,
    )
    raw_output = f"{completed.stdout}\n{completed.stderr}".strip()
    language, confidence = _parse_whisper_detect_language_output(raw_output)
    raw_output_path = output_dir / f"{audio_path.stem}.language_probe.txt"
    raw_output_path.write_text(raw_output + "\n", encoding="utf-8")
    return {
        "engine": "whisper_cpp_detect_language",
        "language": language,
        "confidence": confidence,
        "duration_seconds": duration_seconds,
        "sample_path": probe_path,
        "model_path": model_path,
        "raw_output_path": raw_output_path,
    }


def _clean_funasr_text(text: str) -> str:
    text = SENSEVOICE_TAG_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _funasr_device() -> str:
    configured = os.environ.get("VIDEO_BUNDLE_AGENT_FUNASR_DEVICE") or os.environ.get(
        "FUNASR_DEVICE"
    )
    if configured:
        return configured
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda:0"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"


def _normalize_funasr_item(item: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    raw_sentence_info = item.get("sentence_info") or []
    if not isinstance(raw_sentence_info, list):
        raw_sentence_info = []

    segments: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_sentence_info):
        if not isinstance(raw, dict):
            continue
        start = float(raw.get("start") or raw.get("start_ms") or 0) / 1000
        end = float(raw.get("end") or raw.get("end_ms") or start * 1000) / 1000
        text = _clean_funasr_text(str(raw.get("text") or raw.get("sentence") or ""))
        if not text:
            continue
        speaker = raw.get("spk")
        if speaker is None:
            speaker = raw.get("speaker")
        segments.append(
            {
                "id": f"{run_id}_{index}",
                "start": start,
                "end": max(start, end),
                "duration": max(0.0, end - start),
                "text": text,
                "speaker": str(speaker) if speaker is not None else None,
                "source": run_id,
            }
        )
    if segments:
        return segments

    text = _clean_funasr_text(str(item.get("text") or ""))
    return [
        {
            "id": f"{run_id}_0",
            "start": 0.0,
            "end": 0.0,
            "duration": 0.0,
            "text": text,
            "speaker": None,
            "source": run_id,
        }
    ] if text else []


def transcribe_with_funasr_paraformer(
    audio_path: Path,
    output_dir: Path,
    *,
    language: str = "zh",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        from funasr import AutoModel
    except ImportError as error:
        raise FileNotFoundError("FunASR Python module was not found") from error

    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = "funasr_paraformer_zh"
    model_name = "paraformer-zh"
    device = _funasr_device()
    model = AutoModel(
        model=model_name,
        vad_model="fsmn-vad",
        punc_model="ct-punc",
        spk_model="cam++",
        device=device,
        disable_update=True,
    )
    raw_result = model.generate(input=str(audio_path), batch_size_s=300)
    raw_items = raw_result if isinstance(raw_result, list) else [raw_result]
    segments: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, dict):
            segments.extend(_normalize_funasr_item(item, run_id))

    raw_json_path = output_dir / f"{audio_path.stem}.funasr.raw.json"
    raw_json_path.write_text(
        json.dumps(raw_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return (
        {
            "engine": "funasr",
            "transcript_source": run_id,
            "model_name": model_name,
            "raw_json_path": raw_json_path,
            "language": language,
            "device": device,
        },
        segments,
    )


def build_transcript_payload(
    *,
    source: dict[str, Any],
    segments: list[dict[str, Any]],
    language: str,
    transcript_source: str,
    model_path: Path | None = None,
    language_detection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "fetched_at": datetime.now(UTC).isoformat(),
        "language": language,
        "transcript_source": transcript_source,
        "model_path": str(model_path) if model_path else None,
        "language_detection": _serializable_language_detection(language_detection),
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
            "transcript_source": "whisper_cpp",
            "model_path": model_path,
            "raw_json_path": json_path,
            "language": language,
        },
        parse_whisper_cpp_json(json_path),
    )


def transcribe_audio_for_language(
    audio_path: Path,
    output_dir: Path,
    *,
    language: str = "auto",
    detect_language: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    effective_language = language
    language_detection: dict[str, Any] | None = None
    if detect_language:
        try:
            language_detection = detect_language_with_whisper_cpp(audio_path, output_dir)
            detected_language = language_detection.get("language")
            confidence = language_detection.get("confidence")
            confidence_value = confidence if isinstance(confidence, int | float) else None
            language_detection["accepted"] = _accept_detected_language(
                detected_language if isinstance(detected_language, str) else None,
                float(confidence_value) if confidence_value is not None else None,
            )
            if language_detection["accepted"] and isinstance(detected_language, str):
                effective_language = detected_language
            else:
                language_detection["fallback_language"] = language
        except Exception as error:  # noqa: BLE001
            language_detection = {
                "engine": "whisper_cpp_detect_language",
                "language": None,
                "confidence": None,
                "accepted": False,
                "error": str(error),
                "fallback_language": language,
            }

    if is_chinese_language(effective_language):
        info, segments = transcribe_with_funasr_paraformer(
            audio_path,
            output_dir,
            language=effective_language,
        )
    else:
        info, segments = transcribe_with_whisper_cpp(
            audio_path,
            output_dir,
            language=effective_language,
        )
    info["language_detection"] = language_detection
    info["language"] = effective_language
    return info, segments
