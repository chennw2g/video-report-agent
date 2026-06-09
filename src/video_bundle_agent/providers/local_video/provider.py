from __future__ import annotations

from pathlib import Path
from typing import Any

from video_bundle_agent.bundle.schema import Capabilities, SourceInfo
from video_bundle_agent.bundle.writer import BundleArtifacts, finalize_bundle
from video_bundle_agent.diagnostics.models import DiagnosticLog


def analyze_local_video(source_path: str, output_dir: Path) -> dict[str, Any]:
    diagnostics = DiagnosticLog()
    diagnostics.add(
        code="PLATFORM_UNSUPPORTED",
        severity="error",
        stage="provider",
        message="Local video provider is a phase-1 skeleton only.",
    )
    source = SourceInfo(platform="local_video", source_url=source_path, resolved_url=source_path)
    bundle = finalize_bundle(
        output_dir=output_dir,
        source=source,
        artifacts=BundleArtifacts(),
        capabilities=Capabilities(),
        diagnostics=diagnostics,
        command={"provider": "local_video", "phase": "skeleton"},
    )
    return {
        "status": diagnostics.status,
        "output_dir": str(output_dir),
        "bundle_path": str(output_dir / "bundle.json"),
        "capabilities": bundle.capabilities.model_dump(mode="json"),
    }
