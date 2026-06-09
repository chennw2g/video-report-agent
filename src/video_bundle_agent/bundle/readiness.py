from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _path_exists(bundle_dir: Path, relative_path: str | None) -> bool:
    return bool(relative_path) and (bundle_dir / relative_path).exists()


def _diagnostic_summary(diagnostics: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    records = diagnostics.get("records") or []
    errors = [record for record in records if record.get("severity") == "error"]
    return errors, bool(errors)


def _transcript_evidence(bundle_dir: Path, transcript_path: str | None) -> dict[str, Any]:
    if not _path_exists(bundle_dir, transcript_path):
        return {"available": False, "segment_count": 0}
    payload = _read_json(bundle_dir / str(transcript_path))
    segments = payload.get("segments") or []
    return {"available": bool(segments), "segment_count": len(segments)}


def _slides_evidence(bundle_dir: Path, slides_path: str | None) -> dict[str, Any]:
    if not _path_exists(bundle_dir, slides_path):
        return {"available": False, "candidate_count": 0, "existing_file_count": 0}
    payload = _read_json(bundle_dir / str(slides_path))
    items = payload.get("items") or []
    existing = 0
    for item in items:
        path = item.get("path")
        if path and (bundle_dir / path).exists():
            existing += 1
    return {
        "available": bool(items) and existing > 0,
        "candidate_count": len(items),
        "existing_file_count": existing,
    }


def _comments_evidence(bundle_dir: Path, comments_path: str | None) -> dict[str, Any]:
    if not _path_exists(bundle_dir, comments_path):
        return {"available": False, "count_fetched": 0}
    payload = _read_json(bundle_dir / str(comments_path))
    return {"available": True, "count_fetched": int(payload.get("count_fetched") or 0)}


def evaluate_bundle_readiness(bundle_dir: Path) -> dict[str, Any]:
    bundle_path = bundle_dir / "bundle.json"
    diagnostics_path = bundle_dir / "diagnostics.json"
    if not bundle_path.exists():
        return {
            "schema_version": "0.1.0",
            "bundle_dir": str(bundle_dir),
            "report_ready": False,
            "status": "blocked",
            "blockers": [
                {
                    "code": "BUNDLE_MISSING",
                    "message": "bundle.json was not found.",
                }
            ],
            "warnings": [],
            "evidence": {},
        }
    bundle = _read_json(bundle_path)
    diagnostics = _read_json(diagnostics_path) if diagnostics_path.exists() else {"records": []}

    errors, has_diagnostic_errors = _diagnostic_summary(diagnostics)
    transcript = _transcript_evidence(bundle_dir, bundle.get("transcript_path"))
    slides = _slides_evidence(bundle_dir, bundle.get("slides_path"))
    comments = _comments_evidence(bundle_dir, bundle.get("comments_path"))

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if has_diagnostic_errors:
        for error in errors:
            blockers.append(
                {
                    "code": error.get("code") or "DIAGNOSTIC_ERROR",
                    "message": error.get("message") or "Bundle diagnostics contain an error.",
                    "stage": error.get("stage"),
                }
            )

    if not transcript["available"]:
        blockers.append(
            {
                "code": "TRANSCRIPT_REQUIRED",
                "message": "A substantive report requires transcript or transcription evidence.",
            }
        )
    if not slides["available"]:
        blockers.append(
            {
                "code": "VISUAL_EVIDENCE_REQUIRED",
                "message": "A substantive report requires screenshots, slides, or keyframes.",
            }
        )
    if not comments["available"]:
        warnings.append(
            {
                "code": "COMMENTS_MISSING",
                "message": (
                    "Audience feedback is missing; the main content report can still proceed."
                ),
            }
        )

    report_ready = not blockers
    return {
        "schema_version": "0.1.0",
        "bundle_dir": str(bundle_dir),
        "report_ready": report_ready,
        "status": "ready" if report_ready else "blocked",
        "blockers": blockers,
        "warnings": warnings,
        "evidence": {
            "metadata": {
                "available": _path_exists(bundle_dir, bundle.get("metadata_path")),
            },
            "transcript": transcript,
            "slides": slides,
            "comments": comments,
            "diagnostics": {
                "error_count": len(errors),
                "record_count": len(diagnostics.get("records") or []),
            },
        },
    }
