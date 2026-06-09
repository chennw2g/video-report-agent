from pathlib import Path

from video_bundle_agent.bundle.evidence import select_report_evidence
from video_bundle_agent.bundle.writer import write_json, write_text


def _write_bundle(tmp_path: Path) -> None:
    write_json(
        tmp_path / "bundle.json",
        {
            "schema_version": "0.1.0",
            "source": {"platform": "youtube", "source_url": "url", "source_id": "id"},
            "metadata_path": "metadata.json",
            "transcript_path": "transcript.segments.json",
            "transcript_text_path": "transcript.txt",
            "transcript_comparison_path": "transcript.comparison.json",
            "comments_path": None,
            "danmaku_path": None,
            "audience_feedback_path": None,
            "slides_path": "slides.json",
            "diagnostics_path": "diagnostics.json",
            "manifest_path": "manifest.json",
            "capabilities": {
                "has_metadata": True,
                "has_transcript": True,
                "has_comments": False,
                "has_danmaku": False,
                "has_audience_feedback": False,
                "has_slides": True,
                "has_ocr": False,
            },
        },
    )
    write_json(tmp_path / "diagnostics.json", {"records": []})
    write_json(tmp_path / "metadata.json", {"title": "Example"})
    write_json(
        tmp_path / "transcript.segments.json",
        {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Intro"},
                {"start": 10.0, "end": 12.0, "text": "Click here for the key setting"},
                {"start": 20.0, "end": 22.0, "text": "Result"},
                {"start": 30.0, "end": 32.0, "text": "Closing"},
            ]
        },
    )
    write_text(tmp_path / "transcript.txt", "Intro\nClick here\nResult\nClosing\n")
    write_json(
        tmp_path / "transcript.comparison.json",
        {
            "items": [
                {
                    "start": 0.0,
                    "end": 15.0,
                    "similarity": 0.72,
                    "flagged": True,
                    "term_differences": {
                        "primary_only": ["computer"],
                        "alternative_only": ["compute"],
                    },
                    "word_differences": {
                        "primary_only": ["computer"],
                        "alternative_only": ["compute"],
                    },
                    "primary_text": "They have computer already.",
                    "alternative_text": "They have compute already.",
                }
            ]
        },
    )
    items = []
    for index, timestamp in enumerate([0.0, 10.0, 20.0, 30.0], start=1):
        screenshot = tmp_path / "screenshots" / "candidates" / f"{timestamp:08.1f}s_fixed.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        screenshot.write_bytes(b"png")
        items.append(
            {
                "id": f"slide_{index:04d}",
                "timestamp": timestamp,
                "path": screenshot.relative_to(tmp_path).as_posix(),
            }
        )
    write_json(tmp_path / "slides.json", {"items": items})


def test_select_report_evidence_prefers_keyword_and_limits_images(tmp_path: Path) -> None:
    _write_bundle(tmp_path)

    result = select_report_evidence(tmp_path, max_images=2)

    assert result["report_ready"] is True
    assert result["selection"]["selected_count"] == 2
    assert result["selected_images"][0]["timestamp"] == 10.0
    assert result["selected_images"][0]["selection_reasons"] == ["keyword_nearby"]
    assert result["selected_images"][0]["transcript_window"]
    assert result["selected_images"][0]["transcript_comparison_windows"]


def test_select_report_evidence_returns_blockers_for_unready_bundle(tmp_path: Path) -> None:
    write_json(tmp_path / "bundle.json", {"schema_version": "0.1.0"})
    write_json(tmp_path / "diagnostics.json", {"records": []})

    result = select_report_evidence(tmp_path)

    assert result["report_ready"] is False
    assert result["selected_images"] == []
