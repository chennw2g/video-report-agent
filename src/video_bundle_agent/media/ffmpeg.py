from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from video_bundle_agent.tools.paths import find_executable
from video_bundle_agent.tools.process import run_command


def ffprobe_json(path: Path) -> str:
    ffprobe = find_executable("ffprobe")
    if not ffprobe:
        raise FileNotFoundError("ffprobe was not found")
    completed = run_command(
        [
            ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            path,
        ],
        timeout_seconds=60,
    )
    return completed.stdout


def ffprobe_data(path: Path) -> dict[str, Any]:
    return json.loads(ffprobe_json(path))


def extract_audio_wav(
    input_path: Path,
    output_path: Path,
    *,
    sample_rate: int = 16000,
    timeout_seconds: int = 1800,
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
            "-i",
            input_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "wav",
            output_path,
        ],
        timeout_seconds=timeout_seconds,
    )
    return output_path


def mux_video_audio(
    *,
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    timeout_seconds: int = 1800,
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
            "-i",
            video_path,
            "-i",
            audio_path,
            "-c",
            "copy",
            output_path,
        ],
        timeout_seconds=timeout_seconds,
    )
    return output_path
