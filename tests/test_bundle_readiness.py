from pathlib import Path

from video_bundle_agent.bundle.readiness import evaluate_bundle_readiness
from video_bundle_agent.bundle.writer import write_json, write_text


def _write_base_bundle(tmp_path: Path, *, has_slides: bool = True) -> None:
    write_json(
        tmp_path / "bundle.json",
        {
            "schema_version": "0.1.0",
            "source": {
                "platform": "youtube",
                "source_url": "https://example.test/watch?v=1",
                "resolved_url": "https://example.test/watch?v=1",
                "source_id": "1",
            },
            "metadata_path": "metadata.json",
            "transcript_path": "transcript.segments.json",
            "transcript_text_path": "transcript.txt",
            "comments_path": "comments.json",
            "danmaku_path": None,
            "audience_feedback_path": "audience_feedback.json",
            "slides_path": "slides.json" if has_slides else None,
            "diagnostics_path": "diagnostics.json",
            "manifest_path": "manifest.json",
            "capabilities": {
                "has_metadata": True,
                "has_transcript": True,
                "has_comments": True,
                "has_danmaku": False,
                "has_audience_feedback": True,
                "has_slides": has_slides,
                "has_ocr": False,
            },
        },
    )
    write_json(tmp_path / "diagnostics.json", {"schema_version": "0.1.0", "records": []})
    write_json(tmp_path / "metadata.json", {"title": "Example"})
    write_json(
        tmp_path / "transcript.segments.json",
        {"segments": [{"start": 0, "end": 1, "text": "Hello"}]},
    )
    write_text(tmp_path / "transcript.txt", "Hello\n")
    write_json(tmp_path / "comments.json", {"count_fetched": 0, "items": []})
    write_json(tmp_path / "audience_feedback.json", {"has_comments": True})
    if has_slides:
        screenshot = tmp_path / "screenshots" / "candidates" / "000000.0s_fixed.png"
        screenshot.parent.mkdir(parents=True)
        screenshot.write_bytes(b"png")
        write_json(
            tmp_path / "slides.json",
            {"items": [{"timestamp": 0.0, "path": "screenshots/candidates/000000.0s_fixed.png"}]},
        )


def test_ready_bundle_requires_transcript_and_visual_evidence(tmp_path: Path) -> None:
    _write_base_bundle(tmp_path)

    result = evaluate_bundle_readiness(tmp_path)

    assert result["report_ready"] is True
    assert result["status"] == "ready"
    assert result["evidence"]["slides"]["candidate_count"] == 1


def test_bundle_without_slides_is_blocked(tmp_path: Path) -> None:
    _write_base_bundle(tmp_path, has_slides=False)

    result = evaluate_bundle_readiness(tmp_path)

    assert result["report_ready"] is False
    assert result["status"] == "blocked"
    assert {blocker["code"] for blocker in result["blockers"]} == {"VISUAL_EVIDENCE_REQUIRED"}


def test_diagnostic_errors_block_report(tmp_path: Path) -> None:
    _write_base_bundle(tmp_path)
    write_json(
        tmp_path / "diagnostics.json",
        {
            "schema_version": "0.1.0",
            "records": [
                {
                    "code": "FRAME_EXTRACTION_FAILED",
                    "severity": "error",
                    "stage": "visual_recall",
                    "message": "ffmpeg failed",
                }
            ],
        },
    )

    result = evaluate_bundle_readiness(tmp_path)

    assert result["report_ready"] is False
    assert result["blockers"][0]["code"] == "FRAME_EXTRACTION_FAILED"
