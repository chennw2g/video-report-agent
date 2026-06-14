from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CSS = """
:root {
  color-scheme: light;
  --page: #eef3f6;
  --surface: #ffffff;
  --surface-soft: #f7fafb;
  --nav: #17243a;
  --nav-muted: #9fb0c6;
  --ink: #223041;
  --muted: #627083;
  --line: #dbe4ea;
  --line-strong: #c7d3dc;
  --accent: #0e8f91;
  --accent-dark: #0f6f70;
  --green: #1f7a4d;
  --amber: #b87918;
  --rose: #b85461;
  --shadow: 0 14px 38px rgba(32, 49, 66, 0.08);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  overflow-x: hidden;
  background: var(--page);
  color: var(--ink);
  font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.76;
  letter-spacing: 0;
}
a { color: inherit; text-decoration: none; }
.layout {
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr);
  min-height: 100vh;
}
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 24px 18px;
  background: var(--nav);
  color: #edf4fa;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.brand-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--accent);
  color: white;
  font-weight: 800;
}
.brand-title { font-size: 14px; font-weight: 800; }
.nav { display: grid; gap: 6px; margin-top: 18px; }
.nav a {
  display: block;
  padding: 9px 10px;
  border-radius: 8px;
  color: #d6e0ed;
  font-size: 14px;
}
.nav a:hover { background: rgba(255, 255, 255, 0.08); color: white; }
.main {
  width: 100%;
  max-width: 1220px;
  margin: 0 auto;
  padding: 28px 38px 64px;
}
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.18fr) minmax(320px, 0.82fr);
  gap: 28px;
  align-items: center;
  padding: 30px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.hero-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.eyebrow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: var(--accent-dark);
  font-size: 13px;
  font-weight: 800;
}
h1 {
  margin: 0 0 16px;
  font-size: 40px;
  line-height: 1.16;
  letter-spacing: 0;
}
h1.title-long { font-size: 36px; }
h1.title-very-long { font-size: 32px; }
.lead {
  max-width: 760px;
  margin: 0;
  color: #405064;
  font-size: 17px;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}
.tag,
.label-badge,
.status-badge {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 26px;
  padding: 4px 9px;
  border-radius: 8px;
  background: #edf7f7;
  color: var(--accent-dark);
  font-size: 12px;
  font-weight: 700;
}
.tag {
  flex: 0 1 auto;
}
.label-badge { background: #f1f5f7; color: #536274; }
.status-badge.warning { background: #fff6de; color: var(--amber); }
.status-badge.error { background: #fff0f2; color: var(--rose); }
.hero-media {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  align-self: center;
  overflow: hidden;
  border-radius: 8px;
  background: transparent;
}
.hero-media img {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
  background: transparent;
}
.hero-media.hero-portrait {
  aspect-ratio: 3 / 2;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--line);
  background: var(--surface-soft);
}
.hero-media.hero-portrait img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.hero-media .caption {
  padding: 12px 14px 14px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 13px;
}
.hero-media .caption strong {
  display: block;
  margin-bottom: 3px;
  color: var(--ink);
  font-size: 14px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;
}
.metric-card {
  display: grid;
  grid-template-rows: minmax(30px, 1fr) auto;
  align-items: stretch;
  gap: 2px;
  min-width: 0;
  min-height: 62px;
  padding: 9px 11px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-soft);
}
.metric-value {
  align-self: center;
  min-width: 0;
  white-space: nowrap;
  color: var(--ink);
  font-size: 20px;
  font-weight: 850;
  line-height: 1.25;
}
.metric-value.metric-long { font-size: 18px; }
.metric-value.metric-very-long { font-size: 16px; }
.metric-label {
  align-self: end;
  margin-top: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.2;
}
.module {
  margin-top: 28px;
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: 0 8px 24px rgba(32, 49, 66, 0.05);
}
.module-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}
.module-index {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--accent);
  color: white;
  font-size: 12px;
  font-weight: 900;
}
h2 { margin: 0; font-size: 23px; line-height: 1.35; }
h3 { margin: 0 0 9px; font-size: 18px; line-height: 1.45; }
p { margin: 0 0 12px; }
p:last-child { margin-bottom: 0; }
.body-text { color: #35485a; }
.body-text ul,
.plain-list {
  margin: 10px 0 0;
  padding-left: 1.2em;
}
.body-text li,
.plain-list li { margin-bottom: 6px; }
.evaluation-grid {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 24px;
  align-items: center;
}
.radar-card {
  display: grid;
  place-items: center;
  min-height: 320px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-soft);
}
.radar-card svg { width: 100%; max-width: 360px; height: auto; }
.score-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.score-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  min-height: 48px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-soft);
}
.score-name { color: #3b4c5d; font-weight: 700; }
.score-value { color: var(--accent-dark); font-weight: 900; white-space: nowrap; }
.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: 20px;
  align-items: start;
}
.timeline {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 8px;
}
table { width: 100%; border-collapse: collapse; }
th,
td {
  padding: 11px 12px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
  color: #36485a;
  font-size: 14px;
}
th {
  background: #f1f6f8;
  color: #263648;
  font-weight: 850;
}
tr:last-child td { border-bottom: 0; }
.time-pill {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 8px;
  background: #e7f3f3;
  color: var(--accent-dark);
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}
.analysis-stack { display: grid; gap: 16px; }
.analysis-block {
  padding: 18px 0;
  border-top: 1px solid var(--line);
}
.analysis-block:first-child { padding-top: 0; border-top: 0; }
.block-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.block-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 0.72fr);
  gap: 18px;
  align-items: start;
}
.block-grid.no-media { grid-template-columns: 1fr; }
.media-stack { display: grid; gap: 12px; }
.media-stack.media-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
}
.media-frame {
  overflow: hidden;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: var(--surface-soft);
}
.media-frame img {
  display: block;
  width: 100%;
  max-height: 520px;
  object-fit: contain;
  background: #eef3f6;
}
.media-grid .media-frame img { max-height: 300px; }
.media-caption {
  padding: 10px 12px 12px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 13px;
}
.media-caption strong {
  display: block;
  margin-bottom: 3px;
  color: var(--ink);
}
.comment-list { display: grid; gap: 10px; margin-top: 12px; }
blockquote.comment {
  margin: 0;
  padding: 12px 14px;
  border-left: 4px solid var(--accent);
  border-radius: 0 8px 8px 0;
  background: #f3f8f8;
}
.comment p { margin-bottom: 8px; color: #334556; }
.comment-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--muted);
  font-size: 12px;
}
.callout {
  padding: 14px 16px;
  border: 1px solid #f0d9a6;
  border-radius: 8px;
  background: #fff9eb;
  color: #775313;
}
.trust-list { display: grid; gap: 10px; }
.trust-item {
  padding: 13px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-soft);
}
.trust-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
  font-weight: 850;
}
.footer-note {
  margin-top: 28px;
  color: var(--muted);
  font-size: 13px;
}
.empty {
  padding: 14px 16px;
  border: 1px dashed var(--line-strong);
  border-radius: 8px;
  color: var(--muted);
  background: var(--surface-soft);
}
@media (max-width: 1020px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar {
    position: static;
    height: auto;
  }
  .main { padding: 22px; }
  .hero,
  .evaluation-grid,
  .overview-grid,
  .block-grid,
  .media-stack.media-grid { grid-template-columns: 1fr; }
  .hero-media img {
    height: auto;
    min-height: 0;
  }
  .metrics,
  .score-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  h1 { font-size: 32px; }
  h1.title-long,
  h1.title-very-long { font-size: 30px; }
}
@media (max-width: 620px) {
  .main { padding: 16px; }
  .hero,
  .module { padding: 18px; }
  .metrics,
  .score-list { grid-template-columns: 1fr; }
  h1 { font-size: 28px; }
}
@media print {
  body { background: #ffffff; }
  .layout { display: block; }
  .sidebar { display: none; }
  .main {
    max-width: none;
    padding: 0;
  }
  .hero,
  .module,
  .media-frame,
  .timeline,
  .metric-card,
  .score-item,
  .trust-item {
    break-inside: avoid;
    box-shadow: none;
  }
}
"""

FIT_SCRIPT = """
<script>
(function () {
  function numberPx(value) {
    return Number.parseFloat(value) || 0;
  }

  function fitOneLine(element, minSize) {
    var computed = window.getComputedStyle(element);
    var size = numberPx(element.dataset.baseSize || computed.fontSize);
    element.style.fontSize = size + "px";
    element.style.whiteSpace = "nowrap";
    for (var index = 0; index < 36; index += 1) {
      if (element.scrollWidth <= element.clientWidth || size <= minSize) {
        break;
      }
      size -= 0.5;
      element.style.fontSize = size + "px";
    }
  }

  function fitLines(element, maxLines, minSize) {
    var computed = window.getComputedStyle(element);
    var size = numberPx(element.dataset.baseSize || computed.fontSize);
    element.style.fontSize = size + "px";
    element.style.overflow = "visible";
    for (var index = 0; index < 36; index += 1) {
      var next = window.getComputedStyle(element);
      var lineHeight = numberPx(next.lineHeight) || size * 1.16;
      if (element.scrollHeight <= lineHeight * maxLines + 2 || size <= minSize) {
        break;
      }
      size -= 0.5;
      element.style.fontSize = size + "px";
    }
  }

  function fitAll() {
    document.querySelectorAll("[data-fit-one-line]").forEach(function (element) {
      fitOneLine(element, 11);
    });
    document.querySelectorAll("[data-fit-lines]").forEach(function (element) {
      fitLines(element, Number(element.dataset.fitLines || 2), 24);
    });
  }

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(fitAll);
  }
  window.addEventListener("load", fitAll);
  window.addEventListener("resize", fitAll);
  fitAll();
}());
</script>
"""


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        texts: list[str] = []
        for item in value.values():
            texts.extend(_iter_text_values(item))
        return texts
    if isinstance(value, list | tuple):
        texts = []
        for item in value:
            texts.extend(_iter_text_values(item))
        return texts
    return []


def suspect_encoding_reasons(content: dict[str, Any]) -> list[str]:
    joined = "\n".join(_iter_text_values(content))
    if not joined:
        return []
    reasons: list[str] = []
    if "\ufffd" in joined:
        reasons.append("replacement character U+FFFD was found")
    if re.search(r"\?{4,}", joined):
        reasons.append("long runs of question marks were found")
    question_count = joined.count("?")
    if len(joined) >= 500 and question_count >= 30 and question_count / len(joined) >= 0.02:
        reasons.append("question-mark density is unusually high")
    return reasons


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def append_timing(
    bundle_dir: Path,
    *,
    name: str,
    started_at: str,
    elapsed_seconds: float,
    status: str,
    details: dict[str, Any],
) -> None:
    path = bundle_dir / "timings.json"
    if path.exists():
        try:
            payload = read_json(path)
        except Exception:  # noqa: BLE001
            payload = {}
    else:
        payload = {}
    stages = [item for item in payload.get("stages") or [] if isinstance(item, dict)]
    stages.append(
        {
            "name": name,
            "status": status,
            "started_at": started_at,
            "ended_at": datetime.now(UTC).isoformat(),
            "elapsed_seconds": round(elapsed_seconds, 3),
            "details": details,
        }
    )
    total = round(sum(float(stage.get("elapsed_seconds") or 0) for stage in stages), 3)
    path.write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "generated_at": datetime.now(UTC).isoformat(),
                "total_recorded_seconds": total,
                "stages": stages,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    refresh_manifest_timing_entry(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def refresh_manifest_timing_entry(timings_path: Path) -> None:
    manifest_path = timings_path.parent / "manifest.json"
    if not manifest_path.exists():
        return
    try:
        manifest = read_json(manifest_path)
    except Exception:  # noqa: BLE001
        return
    files = manifest.get("files")
    if not isinstance(files, list):
        return
    entry = {
        "path": timings_path.name,
        "kind": "timings",
        "size_bytes": timings_path.stat().st_size,
        "sha256": sha256_file(timings_path),
    }
    for index, item in enumerate(files):
        if isinstance(item, dict) and item.get("path") == timings_path.name:
            files[index] = entry
            break
    else:
        files.append(entry)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def text(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return ""


def format_int(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value or "")


def format_duration(seconds: Any) -> str:
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    minutes, sec = divmod(total, 60)
    if minutes < 60:
        return f"{minutes} 分 {sec:02d} 秒"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} 小时 {minutes} 分 {sec:02d} 秒"


def format_score(value: Any) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return str(value or "")
    if score.is_integer():
        return str(int(score))
    return f"{score:.1f}"


def relative_asset_path(bundle_dir: Path, value: Any) -> str:
    raw = str(value or "")
    if not raw:
        return ""
    if raw.startswith(("http://", "https://", "data:")):
        return raw
    path = Path(raw)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(bundle_dir.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
    return raw.replace("\\", "/")


def local_asset_path(bundle_dir: Path, value: Any) -> Path | None:
    raw = str(value or "")
    if not raw or raw.startswith(("http://", "https://", "data:")):
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = bundle_dir / path
    return path if path.exists() else None


def image_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as handle:
            header = handle.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                width = int.from_bytes(header[16:20], "big")
                height = int.from_bytes(header[20:24], "big")
                return (width, height) if width and height else None
            if header[:2] != b"\xff\xd8":
                return None
            handle.seek(2)
            while True:
                marker_start = handle.read(1)
                if not marker_start:
                    return None
                if marker_start != b"\xff":
                    continue
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if not marker:
                    return None
                marker_value = marker[0]
                if marker_value in {0xD8, 0xD9}:
                    continue
                length_bytes = handle.read(2)
                if len(length_bytes) != 2:
                    return None
                length = int.from_bytes(length_bytes, "big")
                if length < 2:
                    return None
                if 0xC0 <= marker_value <= 0xC3:
                    data = handle.read(length - 2)
                    if len(data) >= 5:
                        height = int.from_bytes(data[1:3], "big")
                        width = int.from_bytes(data[3:5], "big")
                        return (width, height) if width and height else None
                    return None
                handle.seek(length - 2, os.SEEK_CUR)
    except OSError:
        return None


def hero_orientation_class(bundle_dir: Path, visual: dict[str, Any]) -> str:
    explicit = str(visual.get("orientation") or "").lower()
    if explicit in {"portrait", "vertical"}:
        return " hero-portrait"
    local_path = local_asset_path(bundle_dir, visual.get("image_path"))
    dimensions = image_dimensions(local_path) if local_path else None
    if not dimensions:
        return ""
    width, height = dimensions
    return " hero-portrait" if height / max(width, 1) > 1.2 else ""


def paragraphs(value: Any) -> str:
    blocks: list[str] = []
    for item in ensure_list(value):
        if item in (None, ""):
            continue
        if isinstance(item, dict):
            title = item.get("title")
            body = item.get("body") or item.get("text") or item.get("summary")
            if title:
                blocks.append(f"<h3>{text(title)}</h3>")
            blocks.append(paragraphs(body))
        else:
            blocks.append(f"<p>{text(item)}</p>")
    return "\n".join(block for block in blocks if block)


def render_nav(items: list[tuple[str, str]]) -> str:
    return "\n".join(f'<a href="#{anchor}">{text(label)}</a>' for anchor, label in items)


def render_tags(tags: list[str]) -> str:
    return "\n".join(f'<span class="tag">{text(tag)}</span>' for tag in tags if tag)


def default_tags(metadata: dict[str, Any], content: dict[str, Any]) -> list[str]:
    tags = [str(tag) for tag in ensure_list(content.get("tags")) if tag]
    if tags:
        return tags
    source = metadata.get("source") or {}
    fallback = [
        source.get("platform") or metadata.get("extractor"),
        metadata.get("uploader"),
        "图文报告",
    ]
    return [str(tag) for tag in fallback if tag]


def default_metrics(metadata: dict[str, Any], content: dict[str, Any]) -> list[dict[str, str]]:
    metrics = content.get("metrics")
    if isinstance(metrics, list) and metrics:
        return [item for item in metrics if isinstance(item, dict)]

    source = metadata.get("source") or {}
    rows: list[dict[str, str]] = []
    platform = source.get("platform") or metadata.get("extractor")
    if platform:
        rows.append({"label": "平台", "value": str(platform)})
    if metadata.get("uploader"):
        rows.append({"label": "作者", "value": str(metadata["uploader"])})
    duration = format_duration(metadata.get("duration"))
    if duration:
        rows.append({"label": "时长", "value": duration})
    if metadata.get("view_count") is not None:
        rows.append({"label": "播放量", "value": format_int(metadata["view_count"])})
    if metadata.get("like_count") is not None:
        rows.append({"label": "点赞数", "value": format_int(metadata["like_count"])})
    if metadata.get("comment_count") is not None:
        rows.append({"label": "评论数", "value": format_int(metadata["comment_count"])})
    return rows


def render_metrics(metrics: list[dict[str, Any]]) -> str:
    cards = []
    for item in metrics:
        value = str(item.get("value") or "")
        value_class = "metric-value"
        if len(value) > 18:
            value_class += " metric-very-long"
        elif len(value) > 10:
            value_class += " metric-long"
        cards.append(
            '<div class="metric-card">'
            f'<div class="{value_class}" data-fit-one-line>{text(value)}</div>'
            f'<div class="metric-label">{text(item.get("label"))}</div>'
            "</div>"
        )
    return "\n".join(cards)


def title_class(title: str) -> str:
    if len(title) > 34:
        return "title-very-long"
    if len(title) > 22:
        return "title-long"
    return ""


def normalize_visual(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    return {
        "image_path": first_non_empty(item.get("image_path"), item.get("path"), item.get("src")),
        "title": first_non_empty(item.get("title"), item.get("label"), "视频画面"),
        "caption": first_non_empty(item.get("caption"), item.get("description"), item.get("body")),
        "time": first_non_empty(item.get("time"), item.get("timestamp")),
        "source": item.get("source") or item.get("source_reason"),
    }


def section_visuals(item: dict[str, Any]) -> list[dict[str, Any]]:
    values = first_non_empty(
        item.get("visual_evidence"),
        item.get("visuals"),
        item.get("screenshots"),
        item.get("images"),
    )
    return [normalize_visual(visual) for visual in ensure_list(values) if normalize_visual(visual)]


def collect_visuals(content: dict[str, Any]) -> list[dict[str, Any]]:
    visuals = [normalize_visual(item) for item in ensure_list(content.get("visual_evidence"))]
    visuals = [item for item in visuals if item.get("image_path")]
    for section in ensure_list(content.get("sections")):
        if isinstance(section, dict):
            visuals.extend(item for item in section_visuals(section) if item.get("image_path"))
    return visuals


def pick_hero_visual(
    bundle_dir: Path,
    metadata: dict[str, Any],
    content: dict[str, Any],
) -> dict[str, Any]:
    hero = normalize_visual(content.get("hero_visual"))
    if hero.get("image_path"):
        return hero
    thumbnail = (
        metadata.get("thumbnail_path")
        or metadata.get("cover_path")
        or metadata.get("thumbnail")
        or metadata.get("thumbnail_url")
    )
    if thumbnail:
        return {
            "image_path": thumbnail,
            "title": "视频封面",
            "caption": metadata.get("title") or "",
        }
    visuals = collect_visuals(content)
    if visuals:
        return visuals[0]
    bundle = read_json(bundle_dir / "bundle.json")
    source = bundle.get("source") if isinstance(bundle, dict) else {}
    return {
        "image_path": "",
        "title": source.get("source_id") if isinstance(source, dict) else "",
        "caption": "未找到可用于顶部展示的封面或截图。",
    }


def render_media_frame(bundle_dir: Path, visual: dict[str, Any]) -> str:
    image_path = relative_asset_path(bundle_dir, visual.get("image_path"))
    if not image_path:
        return ""
    time_value = visual.get("time")
    meta = f'<span class="label-badge">{text(time_value)}</span>' if time_value else ""
    return (
        '<figure class="media-frame">'
        f'<img src="{text(image_path)}" alt="{text(visual.get("title"))}">'
        '<figcaption class="media-caption">'
        f"{meta}"
        f"<strong>{text(visual.get('title'))}</strong>"
        f"{text(visual.get('caption'))}"
        "</figcaption>"
        "</figure>"
    )


def render_media_stack(bundle_dir: Path, visuals: list[dict[str, Any]]) -> str:
    frames = [render_media_frame(bundle_dir, visual) for visual in visuals]
    return "\n".join(frame for frame in frames if frame)


def render_hero_visual(bundle_dir: Path, visual: dict[str, Any]) -> str:
    image_path = relative_asset_path(bundle_dir, visual.get("image_path"))
    if not image_path:
        return (
            '<div class="hero-media">'
            '<div class="empty">暂无封面或代表截图</div>'
            "</div>"
        )
    orientation_class = hero_orientation_class(bundle_dir, visual)
    return (
        f'<div class="hero-media{orientation_class}">'
        f'<img src="{text(image_path)}" alt="{text(visual.get("title"))}">'
        "</div>"
    )


def render_timeline(rows: list[Any]) -> str:
    if not rows:
        return '<div class="empty">暂无结构化时间线。</div>'
    body = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        time_value = text(first_non_empty(row.get("time"), row.get("range")))
        topic = text(first_non_empty(row.get("topic"), row.get("title")))
        summary = text(first_non_empty(row.get("summary"), row.get("body")))
        body.append(
            "<tr>"
            f'<td><span class="time-pill">{time_value}</span></td>'
            f"<td>{topic}</td>"
            f"<td>{summary}</td>"
            "</tr>"
        )
    if not body:
        return '<div class="empty">暂无结构化时间线。</div>'
    return (
        '<div class="timeline"><table>'
        "<thead><tr><th>时间段</th><th>主题</th><th>主要内容</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table></div>"
    )


def radar_points(
    dimensions: list[dict[str, Any]],
    scale: float,
    radius: float,
    center: float,
    factor: float = 1.0,
) -> list[tuple[float, float]]:
    points = []
    count = len(dimensions)
    for index, dimension in enumerate(dimensions):
        angle = -math.pi / 2 + 2 * math.pi * index / count
        try:
            raw_score = float(dimension.get("score", 0))
        except (TypeError, ValueError):
            raw_score = 0.0
        score = max(0.0, min(scale, raw_score)) / scale
        distance = radius * score * factor
        points.append((center + distance * math.cos(angle), center + distance * math.sin(angle)))
    return points


def svg_point_list(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def render_radar(evaluation: dict[str, Any]) -> str:
    dimensions = [
        item for item in ensure_list(evaluation.get("dimensions")) if isinstance(item, dict)
    ]
    if len(dimensions) < 3:
        return '<div class="empty">暂无足够评分维度，无法生成雷达图。</div>'

    scale = float(evaluation.get("scale") or 5)
    center = 180.0
    radius = 104.0
    grid = []
    for ring in range(1, int(scale) + 1):
        factor = ring / scale
        points = radar_points(dimensions, scale, radius, center, factor=factor)
        grid.append(
            f'<polygon points="{svg_point_list(points)}" fill="none" '
            'stroke="#cfdbe3" stroke-width="1" />'
        )
    axes = []
    labels = []
    for index, dimension in enumerate(dimensions):
        angle = -math.pi / 2 + 2 * math.pi * index / len(dimensions)
        end_x = center + radius * math.cos(angle)
        end_y = center + radius * math.sin(angle)
        label_x = center + (radius + 42) * math.cos(angle)
        label_y = center + (radius + 42) * math.sin(angle)
        anchor = "middle"
        if label_x < center - 20:
            anchor = "end"
        elif label_x > center + 20:
            anchor = "start"
        axes.append(
            f'<line x1="{center:.1f}" y1="{center:.1f}" x2="{end_x:.1f}" '
            f'y2="{end_y:.1f}" stroke="#d8e2e8" stroke-width="1" />'
        )
        labels.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}" '
            'dominant-baseline="middle" fill="#46596b" font-size="11">'
            f'{text(dimension.get("label"))}</text>'
        )
    score_points = radar_points(dimensions, scale, radius, center)
    return (
        '<svg viewBox="0 0 360 360" role="img" aria-label="AI 多维评分雷达图">'
        f"{''.join(grid)}{''.join(axes)}"
        f'<polygon points="{svg_point_list(score_points)}" fill="#0e8f9124" '
        'stroke="#0e8f91" stroke-width="2.5" />'
        f'<circle cx="{center:.1f}" cy="{center:.1f}" r="3" fill="#0e8f91" />'
        f"{''.join(labels)}"
        "</svg>"
    )


def render_evaluation(evaluation: dict[str, Any]) -> str:
    if not evaluation:
        return '<div class="empty">暂无 AI 评分数据。</div>'
    scale = evaluation.get("scale") or 5
    dimensions = [
        item for item in ensure_list(evaluation.get("dimensions")) if isinstance(item, dict)
    ]
    score_cards = []
    for dimension in dimensions:
        score = text(format_score(dimension.get("score")))
        score_cards.append(
            '<div class="score-item">'
            f'<span class="score-name">{text(dimension.get("label"))}</span>'
            f'<span class="score-value">{score} / {text(scale)}</span>'
            "</div>"
        )
    summary = first_non_empty(evaluation.get("summary"), evaluation.get("overall"))
    return (
        '<div class="evaluation-grid">'
        f'<div class="radar-card">{render_radar(evaluation)}</div>'
        '<div>'
        f'<div class="score-list">{"".join(score_cards)}</div>'
        f'<div class="callout" style="margin-top:14px;">{text(summary)}</div>'
        "</div>"
        "</div>"
    )


def render_module(index: int, anchor: str, title: str, body: str) -> str:
    if not body.strip():
        body = '<div class="empty">暂无内容。</div>'
    return (
        f'<section class="module" id="{anchor}">'
        '<div class="module-heading">'
        f'<div class="module-index">{index:02d}</div>'
        f"<h2>{text(title)}</h2>"
        "</div>"
        f"{body}"
        "</section>"
    )


def render_content_block(bundle_dir: Path, item: dict[str, Any]) -> str:
    title = first_non_empty(item.get("title"), item.get("heading"))
    label = first_non_empty(item.get("label"), item.get("role"))
    time_value = first_non_empty(item.get("time"), item.get("timestamp"))
    evidence = item.get("evidence")
    body = first_non_empty(
        item.get("body"),
        item.get("paragraphs"),
        item.get("summary"),
        item.get("description"),
        item.get("points"),
    )
    visuals = [visual for visual in section_visuals(item) if visual.get("image_path")]
    media_html = render_media_stack(bundle_dir, visuals)
    media_class = "media-stack media-grid" if len(visuals) > 1 else "media-stack"
    grid_class = "block-grid" if media_html else "block-grid no-media"
    meta = []
    if label:
        meta.append(f'<span class="label-badge">{text(label)}</span>')
    if time_value:
        meta.append(f'<span class="label-badge">{text(time_value)}</span>')
    if evidence:
        meta.append(f'<span class="label-badge">证据：{text(evidence)}</span>')
    if len(visuals) > 1:
        return (
            '<article class="analysis-block">'
            f'<div class="block-meta">{"".join(meta)}</div>'
            f"<h3>{text(title)}</h3>"
            f'<div class="body-text">{paragraphs(body)}</div>'
            f'<div class="{media_class}">{media_html}</div>'
            "</article>"
        )
    return (
        '<article class="analysis-block">'
        f'<div class="block-meta">{"".join(meta)}</div>'
        f"<h3>{text(title)}</h3>"
        f'<div class="{grid_class}">'
        f'<div class="body-text">{paragraphs(body)}</div>'
        f'<div class="{media_class}">{media_html}</div>'
        "</div>"
        "</article>"
    )


def render_content_blocks(bundle_dir: Path, items: list[Any]) -> str:
    blocks = [
        render_content_block(bundle_dir, item)
        for item in items
        if isinstance(item, dict)
    ]
    if not blocks:
        return '<div class="empty">暂无结构化正文模块。</div>'
    return f'<div class="analysis-stack">{"".join(blocks)}</div>'


def render_overview(bundle_dir: Path, content: dict[str, Any]) -> str:
    overview = first_non_empty(content.get("overview"), content.get("summary"))
    overview_html = f'<div class="body-text">{paragraphs(overview)}</div>'
    visuals = collect_visuals(content)[:1]
    visual_html = render_media_stack(bundle_dir, visuals)
    if visual_html:
        overview_html = (
            '<div class="overview-grid">'
            f"{overview_html}"
            f'<div class="media-stack">{visual_html}</div>'
            "</div>"
        )
    timeline = render_timeline(ensure_list(content.get("timeline")))
    return f"{overview_html}<div style=\"margin-top:18px;\">{timeline}</div>"


def render_codex_visual(item: dict[str, Any]) -> str:
    title = first_non_empty(item.get("title"), item.get("name"), "AI 整理图表")
    label = first_non_empty(item.get("label"), "AI 整理")
    basis = item.get("basis")
    basis_badge = f'<span class="label-badge">依据：{text(basis)}</span>' if basis else ""
    headers = ensure_list(item.get("headers"))
    rows = ensure_list(item.get("rows"))
    table = ""
    if headers and rows:
        header_html = "".join(f"<th>{text(header)}</th>" for header in headers)
        row_html = []
        for row in rows:
            cells = row if isinstance(row, list) else ensure_list(row)
            row_html.append(
                "<tr>" + "".join(f"<td>{text(cell)}</td>" for cell in cells) + "</tr>"
            )
        table = (
            '<div class="timeline"><table>'
            f"<thead><tr>{header_html}</tr></thead><tbody>{''.join(row_html)}</tbody>"
            "</table></div>"
        )
    else:
        table = f'<div class="body-text">{paragraphs(item.get("body") or item.get("data"))}</div>'
    return (
        '<article class="analysis-block">'
        '<div class="block-meta">'
        f'<span class="label-badge">{text(label)}</span>'
        f"{basis_badge}"
        '</div>'
        f"<h3>{text(title)}</h3>"
        f"{table}"
        "</article>"
    )


def render_codex_visuals(items: list[Any]) -> str:
    blocks = [render_codex_visual(item) for item in items if isinstance(item, dict)]
    if not blocks:
        return ""
    return f'<div class="analysis-stack">{"".join(blocks)}</div>'


def render_representative_comments(comments: list[Any]) -> str:
    blocks = []
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        quote = first_non_empty(comment.get("text"), comment.get("quote"), comment.get("summary"))
        if not quote:
            continue
        meta = []
        if comment.get("author_name"):
            meta.append(f"作者：{text(comment.get('author_name'))}")
        if comment.get("like_count") is not None:
            meta.append(f"点赞数：{text(format_int(comment.get('like_count')))}")
        if comment.get("reply_count") is not None:
            meta.append(f"回复数：{text(format_int(comment.get('reply_count')))}")
        blocks.append(
            '<blockquote class="comment">'
            f"<p>{text(quote)}</p>"
            f'<div class="comment-meta">{"".join(f"<span>{item}</span>" for item in meta)}</div>'
            "</blockquote>"
        )
    if not blocks:
        return ""
    return f'<div class="comment-list">{"".join(blocks)}</div>'


def render_audience_feedback(items: list[Any]) -> str:
    if not items:
        return '<div class="empty">暂无可用评论反馈，或评论数据未进入报告输入。</div>'
    blocks = []
    for item in items:
        if not isinstance(item, dict):
            continue
        comments = ensure_list(
            first_non_empty(
                item.get("representative_comments"),
                item.get("comments"),
                item.get("quotes"),
            )
        )
        blocks.append(
            '<article class="analysis-block">'
            '<div class="block-meta"><span class="label-badge">观众反馈</span></div>'
            f"<h3>{text(item.get('title'))}</h3>"
            f'<div class="body-text">{paragraphs(item.get("body"))}</div>'
            f"{render_representative_comments(comments)}"
            "</article>"
        )
    return f'<div class="analysis-stack">{"".join(blocks)}</div>'


def render_critique(content: dict[str, Any]) -> str:
    evaluation = content.get("evaluation") if isinstance(content.get("evaluation"), dict) else {}
    critique = first_non_empty(content.get("codex_critique"), evaluation.get("commentary"))
    blocks = []
    for item in ensure_list(critique):
        if isinstance(item, dict):
            blocks.append(
                '<article class="analysis-block">'
                '<div class="block-meta"><span class="label-badge">AI 解读</span></div>'
                f"<h3>{text(item.get('title'))}</h3>"
                f'<div class="body-text">{paragraphs(item.get("body"))}</div>'
                "</article>"
            )
        elif item:
            blocks.append(
                '<article class="analysis-block">'
                '<div class="block-meta"><span class="label-badge">AI 解读</span></div>'
                f'<div class="body-text">{paragraphs(item)}</div>'
                "</article>"
            )

    if not blocks:
        dimensions = [
            item
            for item in ensure_list(evaluation.get("dimensions"))
            if isinstance(item, dict) and item.get("note")
        ]
        for item in dimensions:
            blocks.append(
                '<article class="analysis-block">'
                '<div class="block-meta"><span class="label-badge">评分理由</span></div>'
                f"<h3>{text(item.get('label'))}</h3>"
                f'<div class="body-text">{paragraphs(item.get("note"))}</div>'
                "</article>"
            )

    if content.get("recommendations"):
        blocks.append(
            '<article class="analysis-block">'
            '<div class="block-meta"><span class="label-badge">补充建议</span></div>'
            "<h3>后续阅读或学习建议</h3>"
            f'<ul class="plain-list">{render_list_items(content.get("recommendations"))}</ul>'
            "</article>"
        )
    if not blocks:
        return '<div class="empty">暂无详细点评。</div>'
    return f'<div class="analysis-stack">{"".join(blocks)}</div>'


def render_list_items(values: Any) -> str:
    return "\n".join(f"<li>{text(value)}</li>" for value in ensure_list(values) if value)


def diagnostic_records(bundle_dir: Path, content: dict[str, Any]) -> list[dict[str, Any]]:
    notes = [
        item for item in ensure_list(content.get("diagnostic_notes")) if isinstance(item, dict)
    ]
    if notes:
        return notes
    diagnostics = read_json(bundle_dir / "diagnostics.json")
    records = diagnostics.get("records") if isinstance(diagnostics, dict) else []
    normalized = []
    for record in ensure_list(records):
        if not isinstance(record, dict):
            continue
        normalized.append(
            {
                "severity": record.get("severity") or record.get("level") or "warning",
                "title": first_non_empty(record.get("code"), record.get("title"), "诊断提示"),
                "body": first_non_empty(
                    record.get("message"),
                    record.get("body"),
                    record.get("detail"),
                ),
            }
        )
    return normalized


def render_diagnostics(bundle_dir: Path, content: dict[str, Any]) -> str:
    records = diagnostic_records(bundle_dir, content)
    if not records:
        return '<div class="empty">当前报告输入未记录影响解读的诊断问题。</div>'
    items = []
    for record in records:
        severity = str(record.get("severity") or "warning").lower()
        status_class = "error" if severity == "error" else "warning"
        diagnostic_body = paragraphs(
            first_non_empty(record.get("body"), record.get("message"))
        )
        items.append(
            '<div class="trust-item">'
            '<div class="trust-title">'
            f'<span class="status-badge {status_class}">{text(severity)}</span>'
            f"{text(first_non_empty(record.get('title'), record.get('code')))}"
            "</div>"
            f'<div class="body-text">{diagnostic_body}</div>'
            "</div>"
        )
    return f'<div class="trust-list">{"".join(items)}</div>'


def render_attention_notes(
    bundle_dir: Path,
    content: dict[str, Any],
    detail_items: list[dict[str, Any]],
    limitations: list[Any],
) -> str:
    records: list[dict[str, Any]] = [
        item for item in ensure_list(content.get("attention_notes")) if isinstance(item, dict)
    ]
    for item in detail_items:
        records.append(
            {
                "severity": item.get("severity") or "note",
                "title": first_non_empty(item.get("title"), item.get("heading"), "视频内容注意点"),
                "body": first_non_empty(
                    item.get("body"),
                    item.get("paragraphs"),
                    item.get("summary"),
                    item.get("description"),
                ),
            }
        )
    records.extend(diagnostic_records(bundle_dir, content))
    if limitations:
        records.append(
            {
                "severity": "note",
                "title": "报告输入注意点",
                "body": limitations,
            }
        )
    if not records:
        return '<div class="empty">当前报告没有需要单独提示的注意事项。</div>'

    items = []
    for record in records:
        severity = str(record.get("severity") or "note").lower()
        status_class = "error" if severity == "error" else "warning"
        note_body = paragraphs(first_non_empty(record.get("body"), record.get("message")))
        evidence = first_non_empty(record.get("evidence"), record.get("source"))
        evidence_badge = (
            f'<span class="label-badge">依据：{text(evidence)}</span>' if evidence else ""
        )
        items.append(
            '<div class="trust-item">'
            '<div class="trust-title">'
            f'<span class="status-badge {status_class}">{text(severity)}</span>'
            f"{text(first_non_empty(record.get('title'), record.get('code'), '注意事项'))}"
            f"{evidence_badge}"
            "</div>"
            f'<div class="body-text">{note_body}</div>'
            "</div>"
        )
    return f'<div class="trust-list">{"".join(items)}</div>'


def render_evidence_files(items: list[Any]) -> str:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            rows.append(f"<tr><td>{text(item)}</td><td></td></tr>")
            continue
        rows.append(
            "<tr>"
            f"<td>{text(item.get('path'))}</td>"
            f"<td>{text(first_non_empty(item.get('purpose'), item.get('description')))}</td>"
            "</tr>"
        )
    if not rows:
        return '<div class="empty">暂无证据文件索引。</div>'
    return (
        '<div class="timeline"><table>'
        "<thead><tr><th>文件</th><th>用途</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div>"
    )


def render_signature(content: dict[str, Any]) -> str:
    signature = content.get("signature")
    if not isinstance(signature, dict):
        signature = {}
    agent = first_non_empty(
        content.get("signature_agent"),
        signature.get("agent"),
        "CODEX",
    )
    model = first_non_empty(
        content.get("signature_model"),
        content.get("powered_by"),
        signature.get("model"),
        "GPT-5 Codex",
    )
    return (
        '<div class="footer-note">'
        f"Generated by {text(agent)} (Powered by {text(model)})"
        "</div>"
    )


def resolve_content_path(bundle_dir: Path, requested: Path | None, mode: str | None) -> Path:
    if requested:
        if requested.exists():
            return requested
        bundled = bundle_dir / requested
        if bundled.exists():
            return bundled
        raise FileNotFoundError(f"Report content JSON not found: {requested}")

    candidates: list[Path] = []
    if mode:
        candidates.append(bundle_dir / f"report.content.{mode}.json")
    else:
        candidates.extend(
            [
                bundle_dir / "report.content.quick.json",
                bundle_dir / "report.content.json",
                bundle_dir / "report.content.deep.json",
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No report content JSON found in {bundle_dir}")


def load_content(
    bundle_dir: Path,
    content_path: Path | None,
    mode: str | None,
) -> tuple[dict[str, Any], Path]:
    path = resolve_content_path(bundle_dir, content_path, mode)
    content = read_json(path)
    if not isinstance(content, dict):
        raise TypeError(f"Report content JSON must be an object: {path}")
    return content, path


def detect_mode(content: dict[str, Any], content_path: Path, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    content_mode = content.get("report_mode") or content.get("mode")
    if content_mode in {"quick", "deep"}:
        return str(content_mode)
    name = content_path.name.lower()
    if ".deep" in name:
        return "deep"
    if ".quick" in name:
        return "quick"
    return None


def default_html_path(bundle_dir: Path, mode: str | None, content_path: Path) -> Path:
    if content_path.name == "report.content.json" and mode is None:
        return bundle_dir / "report.zh.html"
    if mode == "deep":
        return bundle_dir / "report.zh.deep.html"
    if mode == "quick":
        return bundle_dir / "report.zh.quick.html"
    return bundle_dir / "report.zh.html"


def default_pdf_path(bundle_dir: Path, mode: str | None, content_path: Path) -> Path:
    if content_path.name == "report.content.json" and mode is None:
        return bundle_dir / "report.zh.pdf"
    if mode == "deep":
        return bundle_dir / "report.zh.deep.pdf"
    if mode == "quick":
        return bundle_dir / "report.zh.quick.pdf"
    return bundle_dir / "report.zh.pdf"


def default_png_path(bundle_dir: Path, mode: str | None, content_path: Path) -> Path:
    if content_path.name == "report.content.json" and mode is None:
        return bundle_dir / "report.zh.png"
    if mode == "deep":
        return bundle_dir / "report.zh.deep.png"
    if mode == "quick":
        return bundle_dir / "report.zh.quick.png"
    return bundle_dir / "report.zh.png"


def source_line(metadata: dict[str, Any], bundle: dict[str, Any], content: dict[str, Any]) -> str:
    if content.get("source_label"):
        return str(content["source_label"])
    source = metadata.get("source") or bundle.get("source") or {}
    parts = [
        source.get("platform") if isinstance(source, dict) else "",
        metadata.get("uploader"),
        metadata.get("published_at"),
    ]
    return " · ".join(str(part) for part in parts if part)


def render_html(bundle_dir: Path, content: dict[str, Any], mode: str | None = None) -> str:
    metadata = read_json(bundle_dir / "metadata.json")
    metadata = metadata if isinstance(metadata, dict) else {}

    title = str(content.get("title") or metadata.get("title") or "视频图文报告")
    tags = default_tags(metadata, content)
    metrics = default_metrics(metadata, content)
    hero_visual = pick_hero_visual(bundle_dir, metadata, content)
    evaluation = content.get("evaluation") if isinstance(content.get("evaluation"), dict) else {}

    section_items = ensure_list(content.get("sections"))
    chapter_items = ensure_list(content.get("chapter_details"))
    core_items = ensure_list(content.get("core_points"))
    detail_items = ensure_list(content.get("detail_modules"))
    legacy_content_items = [item for item in section_items if isinstance(item, dict)]
    chapter_content_items = [item for item in chapter_items if isinstance(item, dict)]
    core_content_items = [item for item in core_items if isinstance(item, dict)]
    detail_content_items = [item for item in detail_items if isinstance(item, dict)]
    grouped_content = bool(chapter_content_items or core_content_items or legacy_content_items)
    codex_visuals = ensure_list(content.get("codex_visuals"))
    audience_feedback = ensure_list(content.get("audience_feedback"))
    evidence_files = ensure_list(content.get("evidence_files"))
    limitations = ensure_list(content.get("limitations"))

    nav_items: list[tuple[str, str]] = [
        ("evaluation", "AI 评分"),
        ("overview", "视频概要"),
    ]
    if grouped_content:
        if chapter_content_items:
            nav_items.append(("chapters", "章节详解"))
        if core_content_items:
            nav_items.append(("core-points", "核心观点"))
        if legacy_content_items:
            nav_items.append(("analysis", "补充解读"))
    else:
        nav_items.append(("analysis", "正文解读"))
    nav_items.extend(
        [
            ("feedback", "观众反馈"),
        ]
    )
    if codex_visuals:
        nav_items.append(("codex-visuals", "AI 整理"))
    nav_items.extend(
        [
            ("critique", "详细点评"),
            ("attention", "注意事项"),
            ("evidence", "证据索引"),
        ]
    )

    modules = [
        render_module(1, "evaluation", "AI 多维评分概览", render_evaluation(evaluation)),
        render_module(2, "overview", "视频概要与内容地图", render_overview(bundle_dir, content)),
    ]
    next_index = 3
    if grouped_content:
        if chapter_content_items:
            modules.append(
                render_module(
                    next_index,
                    "chapters",
                    "原始章节详解",
                    render_content_blocks(bundle_dir, chapter_content_items),
                )
            )
            next_index += 1
        if core_content_items:
            modules.append(
                render_module(
                    next_index,
                    "core-points",
                    "核心观点深挖",
                    render_content_blocks(bundle_dir, core_content_items),
                )
            )
            next_index += 1
        if legacy_content_items:
            modules.append(
                render_module(
                    next_index,
                    "analysis",
                    "补充解读",
                    render_content_blocks(bundle_dir, legacy_content_items),
                )
            )
            next_index += 1
    else:
        modules.append(
            render_module(
                next_index,
                "analysis",
                "正文解读",
                render_content_blocks(bundle_dir, legacy_content_items),
            )
        )
        next_index += 1

    modules.append(
        render_module(
            next_index,
            "feedback",
            "观众反馈与可见分歧",
            render_audience_feedback(audience_feedback),
        )
    )
    next_index += 1

    if codex_visuals:
        modules.append(
            render_module(
                next_index,
                "codex-visuals",
                "AI 整理图表",
                render_codex_visuals(codex_visuals),
            )
        )
        next_index += 1
    modules.append(
        render_module(
            next_index,
            "critique",
            "AI 详细点评",
            render_critique(content),
        )
    )
    next_index += 1
    modules.append(
        render_module(
            next_index,
            "attention",
            "注意事项",
            render_attention_notes(bundle_dir, content, detail_content_items, limitations),
        )
    )
    next_index += 1
    modules.append(
        render_module(
            next_index,
            "evidence",
            "证据索引",
            render_evidence_files(evidence_files),
        )
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{text(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">VR</div>
        <div>
          <div class="brand-title">Video Report</div>
        </div>
      </div>
      <nav class="nav">{render_nav(nav_items)}</nav>
    </aside>
    <main class="main">
      <header class="hero">
        <div class="hero-copy">
          <h1 class="{text(title_class(title))}" data-fit-lines="2">{text(title)}</h1>
          <div class="tags">{render_tags(tags)}</div>
          <div class="metrics">{render_metrics(metrics)}</div>
        </div>
        {render_hero_visual(bundle_dir, hero_visual)}
      </header>
      {"".join(modules)}
      {render_signature(content)}
    </main>
  </div>
  {FIT_SCRIPT}
</body>
</html>
"""


def find_chrome(explicit: str | None = None) -> str | None:
    candidates = [
        explicit,
        os.environ.get("CHROME"),
        os.environ.get("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("msedge"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def export_pdf(html_path: Path, pdf_path: Path, chrome: str | None = None) -> dict[str, Any]:
    browser = find_chrome(chrome)
    if not browser:
        return {"exported": False, "message": "Chrome/Edge not found"}
    html_path = html_path.resolve()
    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        return {"exported": False, "message": message or f"Chrome exited {result.returncode}"}
    return {"exported": pdf_path.exists(), "message": "ok"}


def export_png(
    html_path: Path,
    png_path: Path,
    *,
    chrome: str | None = None,
    width: int = 1220,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as error:  # noqa: BLE001
        return {"exported": False, "message": f"Playwright unavailable: {error}"}

    html_path = html_path.resolve()
    png_path = png_path.resolve()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    browser_path = find_chrome(chrome)
    launch_options: dict[str, Any] = {"headless": True}
    if browser_path:
        launch_options["executable_path"] = browser_path
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_options)
            page = browser.new_page(
                viewport={"width": max(900, width), "height": 900},
                device_scale_factor=1,
            )
            page.goto(html_path.as_uri(), wait_until="networkidle")
            page.add_style_tag(
                content="""
                .sidebar { display: none !important; }
                .layout { display: block !important; min-height: auto !important; }
                .main {
                  max-width: 1220px !important;
                  margin: 0 auto !important;
                  padding: 28px 38px 64px !important;
                }
                """
            )
            page.locator("main.main").screenshot(path=str(png_path))
            browser.close()
    except Exception as error:  # noqa: BLE001
        return {"exported": False, "message": str(error)}
    return {"exported": png_path.exists(), "message": "ok"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Chinese video report HTML/PDF from content JSON."
    )
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--content", type=Path, default=None)
    parser.add_argument("--mode", choices=["quick", "deep"], default=None)
    parser.add_argument("--html", type=Path, default=None)
    parser.add_argument("--pdf", type=Path, default=None)
    parser.add_argument("--png", type=Path, default=None)
    parser.add_argument("--png-width", type=int, default=1220)
    parser.add_argument("--chrome", type=str, default=None)
    parser.add_argument("--no-pdf", action="store_true")
    parser.add_argument(
        "--allow-suspect-encoding",
        action="store_true",
        help="Render even when report content looks like it was damaged by text encoding.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    run_started_at = datetime.now(UTC).isoformat()
    run_started = time.perf_counter()
    args = parse_args(argv or sys.argv[1:])
    bundle_dir = args.bundle_dir.resolve()
    content, content_path = load_content(bundle_dir, args.content, args.mode)
    if not args.allow_suspect_encoding:
        reasons = suspect_encoding_reasons(content)
        if reasons:
            append_timing(
                bundle_dir,
                name="render_report",
                started_at=run_started_at,
                elapsed_seconds=time.perf_counter() - run_started,
                status="error",
                details={"content_path": str(content_path), "reasons": reasons},
            )
            print(
                (
                    f"Refusing to render suspected mojibake content in {content_path}: "
                    + "; ".join(reasons)
                ),
                file=sys.stderr,
            )
            return 2
    mode = detect_mode(content, content_path, args.mode)
    html_path = args.html or default_html_path(bundle_dir, mode, content_path)
    pdf_path = args.pdf or default_pdf_path(bundle_dir, mode, content_path)
    png_path = args.png or default_png_path(bundle_dir, mode, content_path)

    html_doc = render_html(bundle_dir, content, mode)
    write_text(html_path, html_doc)

    pdf_result = {"exported": False, "message": "disabled"}
    if not args.no_pdf:
        pdf_result = export_pdf(html_path, pdf_path, args.chrome)
    png_result = {"exported": False, "message": "disabled"}
    if args.png:
        png_result = export_png(
            html_path,
            png_path,
            chrome=args.chrome,
            width=args.png_width,
        )

    status = {
        "mode": mode or "default",
        "content_path": str(content_path),
        "html_path": str(html_path),
        "pdf_path": str(pdf_path),
        "pdf_exported": pdf_result["exported"],
        "pdf_message": pdf_result["message"],
        "png_path": str(png_path),
        "png_exported": png_result["exported"],
        "png_message": png_result["message"],
    }
    print(json.dumps(status, ensure_ascii=False, indent=2))
    pdf_ok = args.no_pdf or pdf_result["exported"]
    png_ok = not args.png or png_result["exported"]
    exit_code = 0 if pdf_ok and png_ok else 2
    append_timing(
        bundle_dir,
        name="render_report",
        started_at=run_started_at,
        elapsed_seconds=time.perf_counter() - run_started,
        status="ok" if exit_code == 0 else "error",
        details=status,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
