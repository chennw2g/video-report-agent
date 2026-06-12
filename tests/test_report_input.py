from pathlib import Path

from video_bundle_agent.bundle.report_input import prepare_report_input
from video_bundle_agent.bundle.writer import write_json, write_text


def _write_ready_bundle(tmp_path: Path, *, has_slides: bool = True) -> None:
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
            "transcript_alternatives_path": "transcript.alternatives.json",
            "transcript_comparison_path": "transcript.comparison.json",
            "comments_path": "comments.json",
            "danmaku_path": None,
            "audience_feedback_path": "audience_feedback.json",
            "slides_path": "slides.json" if has_slides else None,
            "diagnostics_path": "diagnostics.json",
            "manifest_path": "manifest.json",
            "content_profile_path": "content_profile.json",
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
    write_json(
        tmp_path / "metadata.json",
        {
            "title": "Example video",
            "description": "Long description",
            "duration": 90,
            "view_count": 1000,
            "like_count": 50,
        },
    )
    write_json(
        tmp_path / "content_profile.json",
        {
            "schema_version": "0.1.0",
            "primary_type": "interview",
            "type_tags": ["interview", "technology"],
            "visual_policy": {"visual_recall": "low", "visual_strategy": "fixed"},
        },
    )
    write_json(
        tmp_path / "transcript.segments.json",
        {
            "transcript_source": "yt_dlp_auto_subtitle",
            "language": "en",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Intro"},
                {"start": 10.0, "end": 12.0, "text": "Click here for the key setting"},
                {"start": 20.0, "end": 22.0, "text": "Result"},
            ],
        },
    )
    write_text(tmp_path / "transcript.txt", "Intro\nClick here for the key setting\nResult\n")
    write_json(
        tmp_path / "transcript.alternatives.json",
        {"items": [{"transcript_path": "transcript.whisper.segments.json"}]},
    )
    write_json(
        tmp_path / "transcript.comparison.json",
        {
            "primary": {"transcript_source": "yt_dlp_auto_subtitle"},
            "alternative": {"transcript_source": "whisper_cpp"},
            "comparison": {"window_count": 1, "flagged_window_count": 1},
            "items": [
                {
                    "start": 0.0,
                    "end": 15.0,
                    "similarity": 0.7,
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
            ],
        },
    )
    write_json(
        tmp_path / "comments.json",
        {
            "count_fetched": 1,
            "items": [
                {
                    "id": "c1",
                    "author_name": "viewer",
                    "text": "Great point",
                    "like_count": 3,
                    "reply_count": 0,
                }
            ],
        },
    )
    write_json(
        tmp_path / "audience_feedback.json",
        {
            "has_comments": True,
            "count_fetched": 1,
            "signals": {"view_count": 1000},
            "stats": {
                "top_liked": [
                    {
                        "id": "c1",
                        "author_name": "viewer",
                        "text": "Great point",
                        "like_count": 3,
                        "reply_count": 0,
                    }
                ]
            },
        },
    )
    if has_slides:
        screenshot = tmp_path / "screenshots" / "candidates" / "000010.0s_fixed.png"
        screenshot.parent.mkdir(parents=True)
        screenshot.write_bytes(b"png")
        write_json(
            tmp_path / "slides.json",
            {
                "items": [
                    {
                        "id": "slide_0001",
                        "timestamp": 10.0,
                        "path": "screenshots/candidates/000010.0s_fixed.png",
                    }
                ]
            },
        )


def test_prepare_report_input_writes_report_input_and_draft(tmp_path: Path) -> None:
    _write_ready_bundle(tmp_path)

    result = prepare_report_input(tmp_path, max_images=1)

    assert result["readiness"]["report_ready"] is True
    assert result["metadata"]["title"] == "Example video"
    assert result["transcript_comparison"]["flagged_window_count"] == 1
    assert result["report_contract"]["default_mode"] == "quick"
    assert result["report_contract"]["report_output_contract_path"] == (
        "docs/report-output-contract.md"
    )
    assert result["report_contract"]["evaluation"]["scale"] == {"min": 1, "max": 5}
    assert result["report_contract"]["evaluation"]["placement"] == {
        "snapshot": "first_content_module_before_video_overview",
        "reasoning": "later_codex_critique_section",
    }
    assert result["report_contract"]["evaluation"]["dimensions"][2]["key"] == "value_density"
    assert "like_count" in result["report_contract"]["audience_feedback_rules"]["deep"]
    assert result["report_contract"]["final_content_paths"]["quick"] == "report.content.quick.json"
    assert result["report_contract"]["final_content_paths"]["deep"] == "report.content.deep.json"
    assert result["selected_evidence"]["selected_images"][0]["transcript_comparison_windows"]
    assert (tmp_path / "report.input.json").exists()
    assert (tmp_path / "report.content.draft.json").exists()

    draft = (tmp_path / "report.content.draft.json").read_text(encoding="utf-8")
    assert "screenshots/candidates/000010.0s_fixed.png" in draft
    assert "Transcript review targets" in draft


def test_prepare_report_input_accepts_visual_selection_plan(tmp_path: Path) -> None:
    _write_ready_bundle(tmp_path)
    write_json(
        tmp_path / "visual_selection_plan.json",
        {
            "schema_version": "0.1.0",
            "source_type": "tutorial",
            "visual_density": "medium",
            "body_screenshot_policy": "selective",
            "semantic_anchors": [
                {
                    "label": "Key setting",
                    "terms": ["key setting"],
                    "need_screenshot": True,
                    "reason": "The setting step needs visual confirmation.",
                }
            ],
        },
    )

    result = prepare_report_input(
        tmp_path,
        max_images=1,
        plan_path=Path("visual_selection_plan.json"),
    )

    assert result["selected_evidence"]["selection"]["selection_strategy"] == "plan_guided"
    assert result["selected_evidence"]["visual_selection_plan"]["available"] is True
    assert result["selected_evidence"]["selected_images"][0]["anchor_label"] == "Key setting"


def test_prepare_report_input_does_not_write_draft_for_blocked_bundle(tmp_path: Path) -> None:
    _write_ready_bundle(tmp_path, has_slides=False)

    result = prepare_report_input(tmp_path, max_images=1)

    assert result["readiness"]["report_ready"] is False
    assert result["generated_paths"]["report_input_path"] == "report.input.json"
    assert result["generated_paths"]["report_content_draft_path"] is None
    assert (tmp_path / "report.input.json").exists()
    assert not (tmp_path / "report.content.draft.json").exists()
