import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from video_bundle_agent.bundle.schema import Capabilities, SourceInfo
from video_bundle_agent.bundle.visual_update import extract_frames_for_bundle
from video_bundle_agent.bundle.writer import BundleArtifacts, finalize_bundle, write_json
from video_bundle_agent.diagnostics.models import DiagnosticLog


def _base_bundle(tmp_path: Path, *, include_video: bool) -> None:
    source = SourceInfo(
        platform="youtube",
        source_url="https://example.test/watch?v=abc",
        source_id="abc",
    )
    artifacts = BundleArtifacts()
    write_json(tmp_path / "metadata.json", {"title": "Example"})
    write_json(
        tmp_path / "transcript.segments.json",
        {"segments": [{"start": 1.0, "end": 2.0, "text": "Look at the chart."}]},
    )
    write_json(tmp_path / "content_profile.json", {"primary_type": "教程"})
    artifacts.add("metadata_path", "metadata", "metadata.json")
    artifacts.add("transcript_path", "transcript", "transcript.segments.json")
    artifacts.add("content_profile_path", "content_profile", "content_profile.json")

    if include_video:
        video_path = tmp_path / "raw" / "media" / "abc.1080p.webm"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"fake video")
        artifacts.add("working_video_path", "raw_media", "raw/media/abc.1080p.webm")

    finalize_bundle(
        output_dir=tmp_path,
        source=source,
        artifacts=artifacts,
        capabilities=Capabilities(has_metadata=True, has_transcript=True),
        diagnostics=DiagnosticLog(),
    )


def test_extract_frames_for_bundle_updates_existing_bundle(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    _base_bundle(tmp_path, include_video=True)
    stale_screenshot = tmp_path / "screenshots" / "candidates" / "stale.png"
    stale_screenshot.parent.mkdir(parents=True, exist_ok=True)
    stale_screenshot.write_bytes(b"stale png")
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"].append(
        {
            "path": "screenshots/candidates/stale.png",
            "kind": "screenshot",
            "size_bytes": stale_screenshot.stat().st_size,
            "sha256": sha256(stale_screenshot.read_bytes()).hexdigest(),
        }
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def fake_create_visual_recall_slides(**kwargs: Any) -> tuple[dict[str, Any], list[Path], list]:
        screenshot_path = (
            kwargs["output_dir"] / "screenshots" / "candidates" / "000001.0s_fixed.png"
        )
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.write_bytes(b"fake png")
        assert kwargs["visual_recall"] == "high"
        assert kwargs["visual_strategy"] == "all"
        assert kwargs["transcript_segments"] == [
            {"start": 1.0, "end": 2.0, "text": "Look at the chart."}
        ]
        return (
            {
                "source": kwargs["source"].model_dump(mode="json"),
                "video": {"path": "raw/media/abc.1080p.webm"},
                "extraction": {"visual_recall": "high", "visual_strategy": "all"},
                "items": [
                    {"id": "slide_0001", "path": "screenshots/candidates/000001.0s_fixed.png"}
                ],
            },
            [screenshot_path],
            [],
        )

    monkeypatch.setattr(
        "video_bundle_agent.bundle.visual_update.create_visual_recall_slides",
        fake_create_visual_recall_slides,
    )

    result = extract_frames_for_bundle(
        tmp_path,
        visual_recall="high",
        visual_strategy="all",
        max_screenshots=10,
    )

    bundle = json.loads((tmp_path / "bundle.json").read_text(encoding="utf-8"))
    assert result["screenshot_count"] == 1
    assert bundle["slides_path"] == "slides.json"
    assert bundle["working_video_path"] == "raw/media/abc.1080p.webm"
    assert bundle["content_profile_path"] == "content_profile.json"
    assert bundle["capabilities"]["has_slides"] is True
    assert not stale_screenshot.exists()
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert sum(1 for item in manifest["files"] if item["kind"] == "screenshot") == 1


def test_extract_frames_for_bundle_records_missing_working_video(tmp_path: Path) -> None:
    _base_bundle(tmp_path, include_video=False)

    result = extract_frames_for_bundle(
        tmp_path,
        visual_recall="medium",
        visual_strategy="auto",
        max_screenshots=10,
    )

    diagnostics = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    codes = [record["code"] for record in diagnostics["records"]]
    assert result["status"] == "error"
    assert "VIDEO_FILE_UNAVAILABLE" in codes
