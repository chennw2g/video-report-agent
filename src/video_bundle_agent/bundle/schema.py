from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from video_bundle_agent.diagnostics.models import utc_now


class SourceInfo(BaseModel):
    platform: str
    source_url: str
    resolved_url: str = ""
    source_id: str = ""


class Capabilities(BaseModel):
    has_metadata: bool = False
    has_transcript: bool = False
    has_comments: bool = False
    has_danmaku: bool = False
    has_audience_feedback: bool = False
    has_slides: bool = False
    has_ocr: bool = False


class BundleIndex(BaseModel):
    schema_version: str = "0.1.0"
    source: SourceInfo
    metadata_path: str | None = None
    transcript_path: str | None = None
    transcript_text_path: str | None = None
    transcript_alternatives_path: str | None = None
    transcript_comparison_path: str | None = None
    comments_path: str | None = None
    danmaku_path: str | None = None
    audience_feedback_path: str | None = None
    source_chapters_path: str | None = None
    media_path: str | None = None
    slides_path: str | None = None
    working_video_path: str | None = None
    working_audio_path: str | None = None
    content_profile_path: str | None = None
    diagnostics_path: str = "diagnostics.json"
    manifest_path: str = "manifest.json"
    capabilities: Capabilities = Field(default_factory=Capabilities)


class ManifestFile(BaseModel):
    path: str
    kind: str
    size_bytes: int
    sha256: str


class Manifest(BaseModel):
    schema_version: str = "0.1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    source: SourceInfo
    files: list[ManifestFile]
    diagnostics_summary: dict[str, Any]
    command: dict[str, Any] = Field(default_factory=dict)
    command_history: list[dict[str, Any]] = Field(default_factory=list)
