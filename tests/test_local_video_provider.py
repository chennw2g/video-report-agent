import json
from pathlib import Path
from typing import Any

from video_bundle_agent.providers.local_video.provider import analyze_local_video


def test_analyze_local_video_writes_bundle_with_transcript_and_slides(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source_video = tmp_path / "input video.mp4"
    source_video.write_bytes(b"video")
    output_dir = tmp_path / "bundle"

    def fake_probe_video_info(video_path: Path) -> dict[str, Any]:
        return {
            "path": video_path,
            "width": 1920,
            "height": 1080,
            "duration": 12.0,
            "frame_rate": 30.0,
            "codec_name": "h264",
            "format_name": "mov,mp4",
            "size_bytes": video_path.stat().st_size,
        }

    def fake_extract_audio_wav(input_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"wav")
        return output_path

    def fake_transcribe_audio_for_language(
        audio_path: Path,
        raw_transcription_dir: Path,
        *,
        language: str = "auto",
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        return (
            {
                "engine": "funasr",
                "transcript_source": "funasr_paraformer_zh",
                "language": "zh",
                "raw_json_path": raw_transcription_dir / f"{audio_path.stem}.raw.json",
            },
            [{"id": "0", "start": 0.0, "end": 2.0, "text": "本地视频转录", "source": "test"}],
        )

    def fake_create_visual_recall_slides(**kwargs: Any) -> tuple[dict[str, Any], list[Path], list]:
        screenshot = kwargs["output_dir"] / "screenshots" / "candidates" / "000000.0s_fixed.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        screenshot.write_bytes(b"png")
        return (
            {
                "source": kwargs["source"].model_dump(mode="json"),
                "video": {"path": "raw/media/input_video.mp4"},
                "extraction": {"visual_recall": kwargs["visual_recall"]},
                "items": [
                    {
                        "id": "slide_0001",
                        "timestamp": 0.0,
                        "path": "screenshots/candidates/000000.0s_fixed.png",
                    }
                ],
            },
            [screenshot],
            [],
        )

    monkeypatch.setattr(
        "video_bundle_agent.providers.local_video.provider.probe_video_info",
        fake_probe_video_info,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.local_video.provider.extract_audio_wav",
        fake_extract_audio_wav,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.local_video.provider.transcribe_audio_for_language",
        fake_transcribe_audio_for_language,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.local_video.provider.create_visual_recall_slides",
        fake_create_visual_recall_slides,
    )

    result = analyze_local_video(
        str(source_video),
        output_dir,
        visual_recall="medium",
        visual_strategy="auto",
    )

    bundle = json.loads((output_dir / "bundle.json").read_text(encoding="utf-8"))
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    audience_feedback = json.loads(
        (output_dir / "audience_feedback.json").read_text(encoding="utf-8")
    )

    assert result["report_ready"] is True
    assert bundle["source"]["platform"] == "local_video"
    assert bundle["working_video_path"] == "raw/media/input_video.mp4"
    assert bundle["comments_path"] is None
    assert bundle["capabilities"]["has_transcript"] is True
    assert bundle["capabilities"]["has_slides"] is True
    assert bundle["capabilities"]["has_comments"] is False
    assert metadata["title"] == "input video"
    assert metadata["duration"] == 12.0
    assert audience_feedback["has_comments"] is False
    assert (output_dir / "transcript.txt").read_text(encoding="utf-8").strip() == "本地视频转录"


def test_analyze_local_video_stage_one_waits_for_later_frame_extraction(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source_video = tmp_path / "input.mp4"
    source_video.write_bytes(b"video")
    output_dir = tmp_path / "bundle"

    monkeypatch.setattr(
        "video_bundle_agent.providers.local_video.provider.probe_video_info",
        lambda video_path: {
            "path": video_path,
            "width": 1280,
            "height": 720,
            "duration": 5.0,
            "frame_rate": 30.0,
            "codec_name": "h264",
            "format_name": "mov,mp4",
            "size_bytes": 5,
        },
    )

    def fake_extract_audio_wav(input_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"wav")
        return output_path

    monkeypatch.setattr(
        "video_bundle_agent.providers.local_video.provider.extract_audio_wav",
        fake_extract_audio_wav,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.local_video.provider.transcribe_audio_for_language",
        lambda *args, **kwargs: (
            {"engine": "whisper_cpp", "transcript_source": "whisper_cpp", "language": "en"},
            [{"id": "0", "start": 0.0, "end": 1.0, "text": "local transcript"}],
        ),
    )

    result = analyze_local_video(str(source_video), output_dir, visual_recall="none")
    bundle = json.loads((output_dir / "bundle.json").read_text(encoding="utf-8"))

    assert result["report_ready"] is False
    assert bundle["capabilities"]["has_transcript"] is True
    assert bundle["capabilities"]["has_slides"] is False
    assert bundle["slides_path"] is None
