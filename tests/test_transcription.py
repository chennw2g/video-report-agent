import json
from pathlib import Path

from video_bundle_agent.media.transcription import (
    parse_whisper_cpp_json,
    whisper_cpp_model_candidates,
    whisper_output_path,
)


def test_parse_whisper_cpp_json_uses_offsets(tmp_path: Path) -> None:
    path = tmp_path / "transcript.json"
    path.write_text(
        json.dumps(
            {
                "transcription": [
                    {
                        "offsets": {"from": 1200, "to": 3400},
                        "text": " hello world ",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    segments = parse_whisper_cpp_json(path)

    assert segments == [
        {
            "id": "0",
            "start": 1.2,
            "end": 3.4,
            "duration": 2.2,
            "text": "hello world",
            "source": "whisper_cpp",
        }
    ]


def test_parse_whisper_cpp_json_uses_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "transcript.json"
    path.write_text(
        json.dumps(
            {
                "transcription": [
                    {
                        "timestamps": {
                            "from": "00:01:02.500",
                            "to": "00:01:05.000",
                        },
                        "text": "timestamped text",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    segments = parse_whisper_cpp_json(path)

    assert segments[0]["start"] == 62.5
    assert segments[0]["end"] == 65.0
    assert segments[0]["duration"] == 2.5


def test_whisper_output_path_preserves_dotted_stem(tmp_path: Path) -> None:
    assert whisper_output_path(tmp_path / "video.16k", ".json").name == "video.16k.json"


def test_whisper_model_candidates_prefer_turbo_before_base() -> None:
    names = [path.name for path in whisper_cpp_model_candidates()]

    assert names.index("ggml-large-v3-turbo.bin") < names.index("ggml-base.bin")


def test_whisper_model_candidates_allow_environment_override(monkeypatch, tmp_path: Path) -> None:
    custom_model = tmp_path / "custom-whisper.bin"
    monkeypatch.setenv("VIDEO_BUNDLE_AGENT_WHISPER_MODEL", str(custom_model))

    assert whisper_cpp_model_candidates()[0] == custom_model
