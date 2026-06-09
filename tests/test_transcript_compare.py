from pathlib import Path

from video_bundle_agent.bundle.transcript_compare import (
    compare_transcript_segments,
    write_transcript_comparison,
)
from video_bundle_agent.bundle.writer import BundleArtifacts, write_json


def test_compare_transcript_segments_flags_technical_term_differences() -> None:
    payload = compare_transcript_segments(
        source={"platform": "youtube"},
        primary={
            "transcript_source": "yt_dlp_auto_subtitle",
            "language": "en",
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "They have plenty of computer already.",
                }
            ],
        },
        alternative={
            "transcript_source": "whisper_cpp",
            "language": "auto",
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "They have plenty of compute already.",
                }
            ],
        },
        alternative_path="transcript.whisper.segments.json",
    )

    assert payload["comparison"]["flagged_window_count"] == 1
    item = payload["items"][0]
    assert item["flagged"] is True
    assert "computer" in item["term_differences"]["primary_only"]
    assert "compute" in item["term_differences"]["alternative_only"]


def test_write_transcript_comparison_can_run_before_bundle_finalize(tmp_path: Path) -> None:
    write_json(
        tmp_path / "transcript.segments.json",
        {
            "source": {"platform": "youtube"},
            "transcript_source": "yt_dlp_auto_subtitle",
            "language": "en",
            "segments": [{"start": 0.0, "end": 5.0, "text": "code design"}],
        },
    )
    write_json(
        tmp_path / "transcript.whisper.segments.json",
        {
            "transcript_source": "whisper_cpp",
            "language": "auto",
            "segments": [{"start": 0.0, "end": 5.0, "text": "co-design"}],
        },
    )
    write_json(
        tmp_path / "transcript.alternatives.json",
        {
            "source": {"platform": "youtube"},
            "primary_transcript_path": "transcript.segments.json",
            "items": [
                {
                    "transcript_path": "transcript.whisper.segments.json",
                    "transcript_source": "whisper_cpp",
                    "language": "auto",
                }
            ],
        },
    )
    artifacts = BundleArtifacts()

    payload = write_transcript_comparison(bundle_dir=tmp_path, artifacts=artifacts)

    assert payload is not None
    assert (tmp_path / "transcript.comparison.json").exists()
    assert artifacts.paths["transcript_comparison_path"] == "transcript.comparison.json"
