import json
from pathlib import Path

from video_bundle_agent.bundle.schema import Capabilities, SourceInfo
from video_bundle_agent.bundle.writer import BundleArtifacts, finalize_bundle, write_json
from video_bundle_agent.diagnostics.models import DiagnosticLog


def test_finalize_bundle_writes_bundle_manifest_and_diagnostics(tmp_path: Path) -> None:
    source = SourceInfo(
        platform="youtube",
        source_url="https://example.test/watch?v=1",
        source_id="1",
    )
    artifacts = BundleArtifacts()
    write_json(tmp_path / "metadata.json", {"title": "Example"})
    artifacts.add("metadata_path", "metadata", "metadata.json")

    bundle = finalize_bundle(
        output_dir=tmp_path,
        source=source,
        artifacts=artifacts,
        capabilities=Capabilities(has_metadata=True),
        diagnostics=DiagnosticLog(),
    )

    assert bundle.schema_version == "0.1.0"
    assert bundle.metadata_path == "metadata.json"
    assert (tmp_path / "bundle.json").exists()
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "diagnostics.json").exists()


def test_finalize_bundle_preserves_manifest_command_history(tmp_path: Path) -> None:
    source = SourceInfo(
        platform="youtube",
        source_url="https://example.test/watch?v=1",
        source_id="1",
    )
    artifacts = BundleArtifacts()
    write_json(tmp_path / "metadata.json", {"title": "Example"})
    artifacts.add("metadata_path", "metadata", "metadata.json")

    finalize_bundle(
        output_dir=tmp_path,
        source=source,
        artifacts=artifacts,
        capabilities=Capabilities(has_metadata=True),
        diagnostics=DiagnosticLog(),
        command={"operation": "analyze", "comments": True},
    )
    finalize_bundle(
        output_dir=tmp_path,
        source=source,
        artifacts=artifacts,
        capabilities=Capabilities(has_metadata=True),
        diagnostics=DiagnosticLog(),
        command={"operation": "extract_frames", "visual_recall": "low"},
    )

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["command"] == {"operation": "extract_frames", "visual_recall": "low"}
    assert [entry["command"]["operation"] for entry in manifest["command_history"]] == [
        "analyze",
        "extract_frames",
    ]
