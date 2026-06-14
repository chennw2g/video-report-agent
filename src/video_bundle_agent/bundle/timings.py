from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class StageTimings:
    def __init__(self, stages: list[dict[str, Any]] | None = None) -> None:
        self.stages = stages or []

    @classmethod
    def load(cls, path: Path) -> StageTimings:
        if not path.exists():
            return cls()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        stages = [item for item in payload.get("stages") or [] if isinstance(item, dict)]
        return cls(stages=stages)

    @contextmanager
    def stage(self, name: str, details: dict[str, Any] | None = None) -> Iterator[None]:
        started_at = _utc_now()
        started = time.perf_counter()
        status = "ok"
        error: dict[str, str] | None = None
        try:
            yield
        except Exception as exc:
            status = "error"
            error = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            ended = time.perf_counter()
            record: dict[str, Any] = {
                "name": name,
                "status": status,
                "started_at": started_at,
                "ended_at": _utc_now(),
                "elapsed_seconds": round(ended - started, 3),
            }
            if details:
                record["details"] = details
            if error:
                record["error"] = error
            self.stages.append(record)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "0.1.0",
            "generated_at": _utc_now(),
            "total_recorded_seconds": round(
                sum(float(stage.get("elapsed_seconds") or 0) for stage in self.stages),
                3,
            ),
            "stages": self.stages,
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _refresh_manifest_timing_entry(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _refresh_manifest_timing_entry(timings_path: Path) -> None:
    manifest_path = timings_path.parent / "manifest.json"
    if not manifest_path.exists():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    files = manifest.get("files")
    if not isinstance(files, list):
        return
    relative_path = timings_path.name
    entry = {
        "path": relative_path,
        "kind": "timings",
        "size_bytes": timings_path.stat().st_size,
        "sha256": _sha256_file(timings_path),
    }
    for index, item in enumerate(files):
        if isinstance(item, dict) and item.get("path") == relative_path:
            files[index] = entry
            break
    else:
        files.append(entry)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
