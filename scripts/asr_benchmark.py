from __future__ import annotations

import argparse
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from video_bundle_agent.media.transcription import (
    build_transcript_payload,
    transcribe_with_whisper_cpp,
)


def _audio_duration(path: Path) -> float:
    import wave

    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def _format_srt_timestamp(seconds: float) -> str:
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    minutes, second = divmod(total, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{second:02d},{milliseconds:03d}"


_SENSEVOICE_TAG_RE = re.compile(r"<\|[^>]+?\|>")
_SENTENCE_BREAKS = set("。！？!?；;")


def _clean_transcript_text(text: str) -> str:
    text = _SENSEVOICE_TAG_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _visible_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _split_text_chunks(text: str, *, max_chars: int = 90) -> list[str]:
    clean_text = _clean_transcript_text(text)
    if not clean_text:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for char in clean_text:
        current.append(char)
        if not char.isspace():
            current_size += 1
        if char in _SENTENCE_BREAKS or current_size >= max_chars:
            chunk = "".join(current).strip()
            if chunk:
                chunks.append(chunk)
            current = []
            current_size = 0
    tail = "".join(current).strip()
    if tail:
        chunks.append(tail)
    return chunks


def _write_outputs(
    *,
    out_dir: Path,
    run_id: str,
    payload: dict[str, Any],
    timings: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    segments = [item for item in payload.get("segments") or [] if isinstance(item, dict)]
    payload = {**payload, "benchmark": timings}
    json_path = out_dir / f"{run_id}.segments.json"
    txt_path = out_dir / f"{run_id}.txt"
    srt_path = out_dir / f"{run_id}.srt"
    timed_path = out_dir / f"{run_id}.timed.txt"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(
        "\n".join(
            str(segment.get("text") or "").strip()
            for segment in segments
            if segment.get("text")
        ),
        encoding="utf-8",
    )
    srt_lines: list[str] = []
    timed_lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = float(segment.get("start") or 0)
        end = float(segment.get("end") or start)
        text = str(segment.get("text") or "").strip()
        speaker = segment.get("speaker")
        prefix = f"{speaker}: " if speaker else ""
        srt_lines.extend(
            [
                str(index),
                f"{_format_srt_timestamp(start)} --> {_format_srt_timestamp(end)}",
                f"{prefix}{text}",
                "",
            ]
        )
        timed_lines.append(
            f"[{_format_srt_timestamp(start).replace(',', '.')}] {prefix}{text}"
        )
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    timed_path.write_text("\n".join(timed_lines), encoding="utf-8")


def _normalize_funasr_item(item: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    text = str(item.get("text") or "").strip()
    raw_sentence_info = item.get("sentence_info") or []
    raw_timestamp = item.get("timestamp") or raw_sentence_info or []
    segments: list[dict[str, Any]] = []

    if isinstance(raw_sentence_info, list) and raw_sentence_info:
        for index, raw in enumerate(raw_sentence_info):
            if not isinstance(raw, dict):
                continue
            start = float(raw.get("start") or raw.get("start_ms") or 0) / 1000
            end = float(raw.get("end") or raw.get("end_ms") or start * 1000) / 1000
            segment_text = _clean_transcript_text(
                str(raw.get("text") or raw.get("sentence") or "").strip()
            )
            if not segment_text:
                continue
            speaker = raw.get("spk")
            if speaker is None:
                speaker = raw.get("speaker")
            segments.append(
                {
                    "id": f"{run_id}_{index}",
                    "start": start,
                    "end": end,
                    "duration": max(0.0, end - start),
                    "text": segment_text,
                    "speaker": str(speaker) if speaker is not None else None,
                    "source": run_id,
                }
            )
    if segments:
        return segments

    timestamp_pairs: list[tuple[float, float]] = []
    if isinstance(raw_timestamp, list):
        for raw in raw_timestamp:
            if (
                isinstance(raw, list | tuple)
                and len(raw) >= 2
                and isinstance(raw[0], int | float)
                and isinstance(raw[1], int | float)
            ):
                timestamp_pairs.append((float(raw[0]) / 1000, float(raw[1]) / 1000))
    if timestamp_pairs and text:
        chunks = _split_text_chunks(text)
        total_units = max(1, _visible_length("".join(chunks)))
        timestamp_count = len(timestamp_pairs)
        cursor = 0
        for index, chunk in enumerate(chunks):
            chunk_units = max(1, _visible_length(chunk))
            start_index = min(timestamp_count - 1, int(cursor / total_units * timestamp_count))
            end_index = min(
                timestamp_count - 1,
                max(start_index, int((cursor + chunk_units) / total_units * timestamp_count) - 1),
            )
            start, _ = timestamp_pairs[start_index]
            _, end = timestamp_pairs[end_index]
            segments.append(
                {
                    "id": f"{run_id}_{index}",
                    "start": start,
                    "end": max(start, end),
                    "duration": max(0.0, end - start),
                    "text": chunk,
                    "speaker": None,
                    "source": run_id,
                }
            )
            cursor += chunk_units
        return segments

    # Some FunASR pipelines return only one punctuated text string.
    text = _clean_transcript_text(text)
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


def _run_funasr(
    *,
    audio_path: Path,
    out_dir: Path,
    source: dict[str, Any],
    run_id: str,
    model: str,
    device: str,
    punc_model: str | None,
    spk_model: str | None,
) -> dict[str, Any]:
    from funasr import AutoModel

    start = time.perf_counter()
    model_kwargs: dict[str, Any] = {
        "model": model,
        "vad_model": "fsmn-vad",
        "device": device,
        "disable_update": True,
    }
    if punc_model:
        model_kwargs["punc_model"] = punc_model
    if spk_model:
        model_kwargs["spk_model"] = spk_model
    model_instance = AutoModel(**model_kwargs)
    model_ready_at = time.perf_counter()
    result = model_instance.generate(input=str(audio_path), batch_size_s=300)
    finished_at = time.perf_counter()
    items = result if isinstance(result, list) else [result]
    segments: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            segments.extend(_normalize_funasr_item(item, run_id))
    duration = _audio_duration(audio_path)
    timings = {
        "run_id": run_id,
        "engine": "funasr",
        "model": model,
        "vad_model": "fsmn-vad",
        "punc_model": punc_model,
        "spk_model": spk_model,
        "device": device,
        "audio_path": str(audio_path),
        "audio_duration_seconds": duration,
        "model_load_seconds": model_ready_at - start,
        "transcription_seconds": finished_at - model_ready_at,
        "total_seconds": finished_at - start,
        "real_time_factor": (finished_at - start) / duration if duration else None,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    payload = build_transcript_payload(
        source=source,
        segments=segments,
        language="auto",
        transcript_source=run_id,
        model_path=None,
    )
    payload["raw_result"] = result
    _write_outputs(out_dir=out_dir, run_id=run_id, payload=payload, timings=timings)
    return timings


def _run_whisper(
    *,
    audio_path: Path,
    out_dir: Path,
    source: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    start = time.perf_counter()
    info, segments = transcribe_with_whisper_cpp(
        audio_path,
        out_dir / "raw_whisper",
        language=language,
    )
    finished_at = time.perf_counter()
    model_path = Path(str(info.get("model_path") or "whisper_cpp"))
    model_name = model_path.stem
    if model_name.startswith("ggml-"):
        model_name = model_name.removeprefix("ggml-")
    run_id = f"whisper_{model_name.replace('-', '_')}"
    duration = _audio_duration(audio_path)
    timings = {
        "run_id": run_id,
        "engine": "whisper_cpp",
        "model": str(info.get("model_path") or ""),
        "device": "whisper.cpp default",
        "audio_path": str(audio_path),
        "audio_duration_seconds": duration,
        "model_load_seconds": None,
        "transcription_seconds": finished_at - start,
        "total_seconds": finished_at - start,
        "real_time_factor": (finished_at - start) / duration if duration else None,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    payload = build_transcript_payload(
        source=source,
        segments=segments,
        language=language,
        transcript_source="whisper_cpp",
        model_path=info.get("model_path"),
    )
    payload["raw_transcription_json_path"] = str(info.get("raw_json_path") or "")
    _write_outputs(out_dir=out_dir, run_id=run_id, payload=payload, timings=timings)
    return timings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--language", default="auto")
    parser.add_argument(
        "--run",
        choices=["all", "whisper", "sensevoice", "paraformer"],
        default="all",
    )
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    source = {
        "platform": args.platform,
        "source_url": args.source_url,
        "source_id": args.source_id,
    }
    runs = []
    if args.run in {"all", "whisper"}:
        runs.append(
            _run_whisper(
                audio_path=args.audio,
                out_dir=args.out,
                source=source,
                language=args.language,
            )
        )
    if args.run in {"all", "sensevoice"}:
        runs.append(
            _run_funasr(
                audio_path=args.audio,
                out_dir=args.out,
                source=source,
                run_id="funasr_sensevoice_small",
                model="iic/SenseVoiceSmall",
                device=args.device,
                punc_model=None,
                spk_model="cam++",
            )
        )
    if args.run in {"all", "paraformer"}:
        runs.append(
            _run_funasr(
                audio_path=args.audio,
                out_dir=args.out,
                source=source,
                run_id="funasr_paraformer_zh",
                model="paraformer-zh",
                device=args.device,
                punc_model="ct-punc",
                spk_model="cam++",
            )
        )
    summary_path = args.out / "timings.json"
    existing = []
    if summary_path.exists():
        existing = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_path.write_text(
        json.dumps([*existing, *runs], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(runs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
