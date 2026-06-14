from pathlib import Path
from typing import Any

from video_bundle_agent.bundle.schema import SourceInfo
from video_bundle_agent.media import visual_recall as visual_recall_module
from video_bundle_agent.media.frame_extractor import (
    FrameCandidate,
    apply_candidate_cap,
    fixed_interval_timestamps,
    format_timestamp_filename,
    interval_for_visual_recall,
    keyword_matches,
    keyword_trigger_candidates,
    parse_scene_change_timestamps,
)
from video_bundle_agent.media.visual_recall import resolve_visual_strategies


def test_visual_recall_intervals_are_fixed() -> None:
    assert interval_for_visual_recall("low") == 15
    assert interval_for_visual_recall("medium") == 5
    assert interval_for_visual_recall("high") == 2


def test_fixed_interval_timestamps_without_cap() -> None:
    timestamps, sampled, skipped = fixed_interval_timestamps(
        duration=16.0,
        interval_seconds=5,
        max_screenshots=0,
    )

    assert timestamps == [0.0, 5.0, 10.0, 15.0]
    assert sampled is False
    assert skipped == 0


def test_fixed_interval_timestamps_with_cap_evenly_samples() -> None:
    timestamps, sampled, skipped = fixed_interval_timestamps(
        duration=100.0,
        interval_seconds=5,
        max_screenshots=5,
    )

    assert len(timestamps) == 5
    assert timestamps[0] == 0.0
    assert timestamps[-1] == 99.9
    assert sampled is True
    assert skipped == 15


def test_format_timestamp_filename() -> None:
    assert format_timestamp_filename(12.5, "fixed") == "000012.5s_fixed.png"


def test_keyword_matches_use_word_boundaries_for_short_finance_terms() -> None:
    assert "pe" not in keyword_matches("People are talking about this market.")
    assert "pe" in keyword_matches("The PE ratio changed the valuation.")
    assert "风险" in keyword_matches("这里要注意现金流风险。")


def test_keyword_trigger_candidates_add_context_frames() -> None:
    candidates, skipped = keyword_trigger_candidates(
        segments=[
            {"start": 10.0, "end": 12.0, "text": "Look at this risk chart."},
            {"start": 11.0, "end": 13.0, "text": "This nearby keyword should dedupe."},
            {"start": 30.0, "end": 32.0, "text": "No visual trigger here."},
        ],
        duration=40.0,
        max_candidates=4,
    )

    assert skipped == 0
    assert [candidate.timestamp for candidate in candidates] == [8.0, 10.0, 12.0, 28.0]
    assert candidates[0].source_reasons == ["keyword_trigger"]
    assert candidates[0].metadata["keyword_matches"]


def test_parse_scene_change_timestamps_respects_gap_and_limit() -> None:
    output = """
    [Parsed_showinfo_1] n:0 pts:100 pts_time:1.2
    [Parsed_showinfo_1] n:1 pts:140 pts_time:1.6
    [Parsed_showinfo_1] n:2 pts:600 pts_time:6.0
    [Parsed_showinfo_1] n:3 pts:1200 pts_time:12.0
    """

    assert parse_scene_change_timestamps(
        output,
        max_scenes=2,
        min_gap_seconds=4.0,
        duration=20.0,
    ) == [1.2, 6.0]


def test_apply_candidate_cap_preserves_focus_and_coverage() -> None:
    candidates = [
        FrameCandidate(timestamp=float(index * 10), source_reasons=["fixed_interval"])
        for index in range(8)
    ]
    candidates.extend(
        [
            FrameCandidate(timestamp=12.0, source_reasons=["keyword_trigger"]),
            FrameCandidate(timestamp=48.0, source_reasons=["scene_change"]),
        ]
    )

    capped, skipped = apply_candidate_cap(candidates, max_candidates=4)

    assert skipped == 6
    assert len(capped) == 4
    reasons = [reason for candidate in capped for reason in candidate.source_reasons]
    assert "keyword_trigger" in reasons
    assert "scene_change" in reasons


def test_apply_candidate_cap_zero_means_unlimited() -> None:
    candidates = [
        FrameCandidate(timestamp=float(index * 10), source_reasons=["fixed_interval"])
        for index in range(8)
    ]

    capped, skipped = apply_candidate_cap(candidates, max_candidates=0)

    assert skipped == 0
    assert len(capped) == 8


def test_visual_recall_records_truncated_coverage(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fake_probe_video_info(video_path: Path) -> dict[str, Any]:
        return {
            "path": video_path,
            "width": 1920,
            "height": 1080,
            "duration": 30.0,
            "frame_rate": 30.0,
            "codec_name": "h264",
            "format_name": "mov,mp4",
            "size_bytes": 1,
        }

    def fake_extract_frame_candidates(**kwargs: Any) -> list[dict[str, object]]:
        output_dir = kwargs["output_dir"]
        candidates = kwargs["candidates"]
        return [
            {
                "id": f"slide_{index:04d}",
                "timestamp": candidate.timestamp,
                "path": output_dir / f"{index:04d}.png",
                "source_reasons": candidate.source_reasons,
            }
            for index, candidate in enumerate(candidates, start=1)
        ]

    monkeypatch.setattr(visual_recall_module, "probe_video_info", fake_probe_video_info)
    monkeypatch.setattr(
        visual_recall_module,
        "extract_frame_candidates",
        fake_extract_frame_candidates,
    )

    slides, screenshot_paths, warnings = visual_recall_module.create_visual_recall_slides(
        source=SourceInfo(platform="youtube", source_url="https://example.test", source_id="abc"),
        source_url="https://example.test",
        video_path=tmp_path / "raw" / "media" / "abc.mp4",
        output_dir=tmp_path,
        visual_recall="high",
        visual_strategy="fixed",
        max_screenshots=2,
        transcript_segments=[],
    )

    extraction = slides["extraction"]
    assert len(screenshot_paths) == 2
    assert extraction["candidate_cap"] == 2
    assert extraction["coverage"]["expected_fixed_interval_count"] == 15
    assert extraction["coverage"]["coverage_truncated"] is True
    assert {warning["code"] for warning in warnings} == {"VISUAL_COVERAGE_TRUNCATED"}


def test_visual_recall_zero_cap_keeps_full_fixed_coverage(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fake_probe_video_info(video_path: Path) -> dict[str, Any]:
        return {
            "path": video_path,
            "width": 1920,
            "height": 1080,
            "duration": 10.0,
            "frame_rate": 30.0,
            "codec_name": "h264",
            "format_name": "mov,mp4",
            "size_bytes": 1,
        }

    def fake_extract_frame_candidates(**kwargs: Any) -> list[dict[str, object]]:
        output_dir = kwargs["output_dir"]
        candidates = kwargs["candidates"]
        return [
            {
                "id": f"slide_{index:04d}",
                "timestamp": candidate.timestamp,
                "path": output_dir / f"{index:04d}.png",
                "source_reasons": candidate.source_reasons,
            }
            for index, candidate in enumerate(candidates, start=1)
        ]

    monkeypatch.setattr(visual_recall_module, "probe_video_info", fake_probe_video_info)
    monkeypatch.setattr(
        visual_recall_module,
        "extract_frame_candidates",
        fake_extract_frame_candidates,
    )

    slides, screenshot_paths, warnings = visual_recall_module.create_visual_recall_slides(
        source=SourceInfo(platform="youtube", source_url="https://example.test", source_id="abc"),
        source_url="https://example.test",
        video_path=tmp_path / "raw" / "media" / "abc.mp4",
        output_dir=tmp_path,
        visual_recall="high",
        visual_strategy="fixed",
        max_screenshots=0,
        transcript_segments=[],
    )

    extraction = slides["extraction"]
    assert len(screenshot_paths) == 5
    assert warnings == []
    assert extraction["candidate_cap"] is None
    assert extraction["candidate_cap_unlimited"] is True
    assert extraction["coverage"]["fixed_interval_coverage_complete"] is True


def test_visual_recall_plan_uses_coarse_sampling_and_semantic_anchors(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fake_probe_video_info(video_path: Path) -> dict[str, Any]:
        return {
            "path": video_path,
            "width": 1920,
            "height": 1080,
            "duration": 120.0,
            "frame_rate": 30.0,
            "codec_name": "h264",
            "format_name": "mov,mp4",
            "size_bytes": 1,
        }

    def fake_extract_frame_candidates(**kwargs: Any) -> list[dict[str, object]]:
        output_dir = kwargs["output_dir"]
        candidates = kwargs["candidates"]
        return [
            {
                "id": f"slide_{index:04d}",
                "timestamp": candidate.timestamp,
                "path": output_dir / f"{index:04d}.png",
                "source_reasons": candidate.source_reasons,
            }
            for index, candidate in enumerate(candidates, start=1)
        ]

    monkeypatch.setattr(visual_recall_module, "probe_video_info", fake_probe_video_info)
    monkeypatch.setattr(
        visual_recall_module,
        "extract_frame_candidates",
        fake_extract_frame_candidates,
    )

    slides, screenshot_paths, warnings = visual_recall_module.create_visual_recall_slides(
        source=SourceInfo(platform="youtube", source_url="https://example.test", source_id="abc"),
        source_url="https://example.test",
        video_path=tmp_path / "raw" / "media" / "abc.mp4",
        output_dir=tmp_path,
        visual_recall="high",
        visual_strategy="all",
        max_screenshots=0,
        transcript_segments=[],
        visual_plan={
            "semantic_anchors": [
                {
                    "id": "anchor_0001",
                    "label": "Result screen",
                    "time_hints": ["00:45-00:55"],
                    "need_screenshot": True,
                },
                {
                    "id": "anchor_0002",
                    "label": "Talking head",
                    "time_hints": ["01:10"],
                    "need_screenshot": False,
                },
            ]
        },
    )

    extraction = slides["extraction"]
    reasons = {
        reason
        for item in slides["items"]
        for reason in item.get("source_reasons", [])
    }
    assert warnings == []
    assert len(screenshot_paths) == 18
    assert extraction["planned_sampling"] is True
    assert extraction["coarse_sampling"] is True
    assert extraction["interval_seconds"] == 8
    assert extraction["fixed_interval"]["candidate_count"] == 15
    assert extraction["semantic_anchor"]["candidate_count"] == 3
    assert "semantic_anchor" in reasons


def test_auto_visual_strategy_keeps_medium_scene_detection_off() -> None:
    assert resolve_visual_strategies(visual_recall="low", visual_strategy="auto") == [
        "fixed_interval"
    ]
    assert resolve_visual_strategies(visual_recall="medium", visual_strategy="auto") == [
        "fixed_interval",
        "keyword_trigger",
    ]
    assert resolve_visual_strategies(visual_recall="high", visual_strategy="auto") == [
        "fixed_interval",
        "keyword_trigger",
        "scene_change",
    ]
