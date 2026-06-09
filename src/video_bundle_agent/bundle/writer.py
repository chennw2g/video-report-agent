from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from video_bundle_agent.bundle.schema import (
    BundleIndex,
    Capabilities,
    Manifest,
    ManifestFile,
    SourceInfo,
)
from video_bundle_agent.diagnostics.models import DiagnosticLog


def _to_jsonable(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    return data


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_to_jsonable(data), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(path: Path, data: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _command_history_entry(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "command": command,
    }


def _entry_command(entry: dict[str, Any]) -> dict[str, Any]:
    command = entry.get("command")
    if isinstance(command, dict):
        return command
    return {}


def _manifest_command_history(
    *,
    manifest_path: Path,
    current_command: dict[str, Any],
) -> list[dict[str, Any]]:
    existing = _read_json_if_exists(manifest_path)
    history = [
        item
        for item in existing.get("command_history", [])
        if isinstance(item, dict) and isinstance(item.get("command"), dict)
    ]
    previous_command = existing.get("command")
    if isinstance(previous_command, dict) and previous_command:
        if not history or _entry_command(history[-1]) != previous_command:
            history.append(_command_history_entry(previous_command))

    if current_command and (not history or _entry_command(history[-1]) != current_command):
        history.append(_command_history_entry(current_command))
    return history


@dataclass
class BundleArtifacts:
    paths: dict[str, str | None] = field(default_factory=dict)
    kinds: dict[str, str] = field(default_factory=dict)

    def add(self, key: str, kind: str, relative_path: str | None) -> None:
        self.paths[key] = relative_path
        if relative_path:
            self.kinds[relative_path] = kind


def finalize_bundle(
    *,
    output_dir: Path,
    source: SourceInfo,
    artifacts: BundleArtifacts,
    capabilities: Capabilities,
    diagnostics: DiagnosticLog,
    command: dict[str, Any] | None = None,
) -> BundleIndex:
    output_dir.mkdir(parents=True, exist_ok=True)
    command_payload = command or {}

    diagnostics_path = "diagnostics.json"
    write_json(output_dir / diagnostics_path, diagnostics)
    artifacts.add("diagnostics_path", "diagnostics", diagnostics_path)

    manifest_files: list[ManifestFile] = []
    for relative_path, kind in sorted(artifacts.kinds.items()):
        path = output_dir / relative_path
        if not path.exists():
            continue
        manifest_files.append(
            ManifestFile(
                path=relative_path,
                kind=kind,
                size_bytes=path.stat().st_size,
                sha256=sha256_file(path),
            )
        )

    manifest = Manifest(
        source=source,
        files=manifest_files,
        diagnostics_summary=diagnostics.summary(),
        command=command_payload,
        command_history=_manifest_command_history(
            manifest_path=output_dir / "manifest.json",
            current_command=command_payload,
        ),
    )
    write_json(output_dir / "manifest.json", manifest)

    bundle = BundleIndex(
        source=source,
        metadata_path=artifacts.paths.get("metadata_path"),
        transcript_path=artifacts.paths.get("transcript_path"),
        transcript_text_path=artifacts.paths.get("transcript_text_path"),
        transcript_alternatives_path=artifacts.paths.get("transcript_alternatives_path"),
        transcript_comparison_path=artifacts.paths.get("transcript_comparison_path"),
        comments_path=artifacts.paths.get("comments_path"),
        danmaku_path=artifacts.paths.get("danmaku_path"),
        audience_feedback_path=artifacts.paths.get("audience_feedback_path"),
        source_chapters_path=artifacts.paths.get("source_chapters_path"),
        media_path=artifacts.paths.get("media_path"),
        slides_path=artifacts.paths.get("slides_path"),
        working_video_path=artifacts.paths.get("working_video_path"),
        working_audio_path=artifacts.paths.get("working_audio_path"),
        content_profile_path=artifacts.paths.get("content_profile_path"),
        diagnostics_path=diagnostics_path,
        manifest_path="manifest.json",
        capabilities=capabilities,
    )
    write_json(output_dir / "bundle.json", bundle)
    return bundle
