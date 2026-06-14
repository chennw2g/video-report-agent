import json
from pathlib import Path

from video_bundle_agent.media.transcription import (
    _accept_detected_language,
    _normalize_funasr_item,
    _parse_whisper_detect_language_output,
    is_chinese_language,
    parse_whisper_cpp_json,
    whisper_cpp_language_model_candidates,
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


def test_whisper_language_model_candidates_prefer_base_before_turbo() -> None:
    names = [path.name for path in whisper_cpp_language_model_candidates()]

    assert names.index("ggml-base.bin") < names.index("ggml-large-v3-turbo.bin")


def test_parse_whisper_detect_language_output_with_confidence() -> None:
    language, confidence = _parse_whisper_detect_language_output(
        "whisper_full_with_state: auto-detected language: zh (p = 0.997134)"
    )

    assert language == "zh"
    assert confidence == 0.997134


def test_parse_whisper_detect_language_output_without_match() -> None:
    language, confidence = _parse_whisper_detect_language_output("no language here")

    assert language is None
    assert confidence is None


def test_accept_detected_language_requires_language_and_reasonable_confidence() -> None:
    assert _accept_detected_language("zh", 0.997)
    assert _accept_detected_language("en", None)
    assert not _accept_detected_language("zh", 0.12)
    assert not _accept_detected_language(None, 0.99)


def test_is_chinese_language_detects_common_language_hints() -> None:
    assert is_chinese_language("zh")
    assert is_chinese_language("zh-Hans")
    assert is_chinese_language("Chinese")
    assert not is_chinese_language("en")
    assert not is_chinese_language("auto")


def test_normalize_funasr_item_preserves_zero_speaker() -> None:
    segments = _normalize_funasr_item(
        {
            "sentence_info": [
                {
                    "text": " hello ",
                    "start": 1000,
                    "end": 2500,
                    "spk": 0,
                }
            ]
        },
        "funasr_paraformer_zh",
    )

    assert segments == [
        {
            "id": "funasr_paraformer_zh_0",
            "start": 1.0,
            "end": 2.5,
            "duration": 1.5,
            "text": "hello",
            "speaker": "0",
            "source": "funasr_paraformer_zh",
        }
    ]
