from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "video-report" / "scripts" / "render_report.py"


def run_renderer(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def make_bundle(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "screenshots" / "candidates").mkdir(parents=True)
    (bundle_dir / "screenshots" / "candidates" / "shot.png").write_bytes(b"png")
    write_json(
        bundle_dir / "bundle.json",
        {
            "source": {
                "platform": "bilibili",
                "source_url": "https://www.bilibili.com/video/BV-test",
                "source_id": "BV-test",
            }
        },
    )
    write_json(
        bundle_dir / "metadata.json",
        {
            "title": "metadata title",
            "duration": 90,
            "uploader": "tester",
            "view_count": 1234,
            "like_count": 56,
            "comment_count": 7,
        },
    )
    write_json(
        bundle_dir / "diagnostics.json",
        {
            "records": [
                {
                    "severity": "warning",
                    "code": "OCR_TOOL_MISSING",
                    "message": "OCR was not available.",
                }
            ]
        },
    )
    return bundle_dir


def test_render_report_script_writes_editorial_lab_deep_html(tmp_path: Path) -> None:
    bundle_dir = make_bundle(tmp_path)
    content_path = bundle_dir / "report.content.deep.json"
    write_json(
        content_path,
        {
            "report_mode": "deep",
            "title": "Deep Renderer Smoke With Longer Title",
            "signature_agent": "CODEX",
            "signature_model": "GPT-5 Codex",
            "summary": "This report checks the finalized visual and content order.",
            "conclusion": "The renderer should keep score before overview.",
            "tags": ["tutorial", "AI video"],
            "evaluation": {
                "scale": 5,
                "summary": "Useful, but tool constraints still matter.",
                "dimensions": [
                    {"label": "可信度", "score": 4, "note": "Evidence is traceable."},
                    {"label": "原创性", "score": 3},
                    {"label": "价值密度", "score": 5},
                    {"label": "论证强度", "score": 4},
                    {"label": "信息密度", "score": 5},
                    {"label": "时效性", "score": 4},
                ],
            },
            "overview": "The overview should come after the AI evaluation snapshot.",
            "timeline": [
                {
                    "time": "00:00-00:30",
                    "topic": "opening",
                    "summary": "sets up the workflow",
                    "evidence": "transcript.txt",
                }
            ],
            "sections": [
                {
                    "label": "视频内容",
                    "title": "Workflow point",
                    "body": ["A section can carry inline screenshots."],
                    "visual_evidence": [
                        {
                            "image_path": "screenshots/candidates/shot.png",
                            "title": "Inline screenshot",
                            "caption": "The image is embedded beside the text.",
                            "time": "00:12",
                        }
                    ],
                }
            ],
            "chapter_details": [
                {
                    "label": "视频内容",
                    "title": "Original chapter",
                    "body": ["Deep reports keep chapter detail in its own module."],
                }
            ],
            "core_points": [
                {
                    "label": "AI 解读",
                    "title": "Core viewpoint",
                    "body": ["The core viewpoint has a separate module."],
                }
            ],
            "detail_modules": [
                {
                    "label": "诊断提示",
                    "title": "Important risk",
                    "body": ["Risks and important details are grouped separately."],
                }
            ],
            "audience_feedback": [
                {
                    "title": "Viewers noticed the same tradeoff",
                    "body": ["The report should show representative comment metadata."],
                    "representative_comments": [
                        {
                            "text": "Short original comment.",
                            "author_name": "viewer",
                            "like_count": 128,
                            "reply_count": 3,
                        }
                    ],
                }
            ],
            "codex_visuals": [
                {
                    "title": "Workflow matrix",
                    "label": "AI 整理",
                    "basis": "transcript.txt",
                    "headers": ["Step", "Meaning"],
                    "rows": [["Prompt", "Plan the shot"]],
                }
            ],
            "codex_critique": [
                {
                    "title": "Why the score is not perfect",
                    "body": ["The renderer keeps detailed reasoning in a later section."],
                }
            ],
            "diagnostic_notes": [
                {
                    "severity": "warning",
                    "title": "Transcript caveat",
                    "body": "Some proper nouns may need manual review.",
                }
            ],
            "evidence_files": [{"path": "metadata.json", "purpose": "source metadata"}],
            "limitations": ["OCR not run."],
        },
    )

    result = run_renderer(
        "--bundle-dir",
        str(bundle_dir),
        "--content",
        str(content_path),
        "--no-pdf",
    )

    assert result.returncode == 0, result.stderr
    html_path = bundle_dir / "report.zh.deep.html"
    html = html_path.read_text(encoding="utf-8")
    assert "color-scheme: light" in html
    assert "This report checks the finalized visual and content order." not in html
    assert "The renderer should keep score before overview." not in html
    assert html.index("AI 多维评分概览") < html.index("视频概要与内容地图")
    assert "原始章节详解" in html
    assert "核心观点深挖" in html
    assert "注意事项" in html
    legacy_detail_title = "重要细节" + "、步骤与风险"
    assert legacy_detail_title not in html
    assert "<th>证据</th>" not in html
    assert html.index("观众反馈与可见分歧") < html.index("AI 整理图表")
    assert "screenshots/candidates/shot.png" in html
    assert "点赞数：128" in html
    assert "Workflow matrix" in html
    assert "Plan the shot" in html
    assert "Important risk" in html
    assert "Transcript caveat" in html
    assert "Why the score is not perfect" in html
    assert 'class="title-very-long"' in html
    assert 'data-fit-lines="2"' in html
    assert "data-fit-one-line" in html
    assert "grid-template-rows: minmax(30px, 1fr) auto" in html
    assert ".metric-label {\n  align-self: end;" in html
    assert "-webkit-line-clamp" not in html
    assert "Generated by CODEX (Powered by GPT-5 Codex)" in html
    assert "Generated from local video-bundle-agent evidence" not in html


def test_render_report_script_keeps_legacy_content_alias(tmp_path: Path) -> None:
    bundle_dir = make_bundle(tmp_path)
    content_path = bundle_dir / "report.content.json"
    write_json(
        content_path,
        {
            "title": "Legacy Renderer Smoke",
            "summary": "Legacy report.content.json should still render to report.zh.html.",
            "visual_evidence": [
                {
                    "image_path": "screenshots/candidates/shot.png",
                    "title": "Legacy screenshot",
                    "caption": "The old global visual evidence field is still accepted.",
                }
            ],
            "sections": [{"title": "Legacy section", "body": ["legacy body"]}],
            "evidence_files": [{"path": "metadata.json", "purpose": "source metadata"}],
        },
    )

    result = run_renderer(
        "--bundle-dir",
        str(bundle_dir),
        "--content",
        str(content_path),
        "--no-pdf",
    )

    assert result.returncode == 0, result.stderr
    html = (bundle_dir / "report.zh.html").read_text(encoding="utf-8")
    assert "Legacy Renderer Smoke" in html
    assert "screenshots/candidates/shot.png" in html
    assert "AI 多维评分概览" in html
    assert "Generated by CODEX (Powered by GPT-5 Codex)" in html


def test_render_report_prefers_metadata_thumbnail_over_body_screenshot(
    tmp_path: Path,
) -> None:
    bundle_dir = make_bundle(tmp_path)
    thumbnail_path = bundle_dir / "raw" / "thumbnail" / "cover.jpg"
    thumbnail_path.parent.mkdir(parents=True)
    thumbnail_path.write_bytes(b"jpg")
    write_json(
        bundle_dir / "metadata.json",
        {
            "title": "metadata title",
            "thumbnail": "https://example.test/cover.jpg",
            "thumbnail_path": "raw/thumbnail/cover.jpg",
            "duration": 90,
        },
    )
    content_path = bundle_dir / "report.content.deep.json"
    write_json(
        content_path,
        {
            "report_mode": "deep",
            "title": "Cover Preference Smoke",
            "summary": "Renderer should use platform cover as the hero visual.",
            "visual_evidence": [
                {
                    "image_path": "screenshots/candidates/shot.png",
                    "title": "Body screenshot",
                }
            ],
            "sections": [{"title": "Body", "body": ["Body copy."]}],
        },
    )

    result = run_renderer(
        "--bundle-dir",
        str(bundle_dir),
        "--content",
        str(content_path),
        "--no-pdf",
    )

    assert result.returncode == 0, result.stderr
    html = (bundle_dir / "report.zh.deep.html").read_text(encoding="utf-8")
    assert html.index("raw/thumbnail/cover.jpg") < html.index("screenshots/candidates/shot.png")


def test_render_report_refuses_suspect_encoding_content(tmp_path: Path) -> None:
    bundle_dir = make_bundle(tmp_path)
    content_path = bundle_dir / "report.content.deep.json"
    write_json(
        content_path,
        {
            "report_mode": "deep",
            "title": "??????",
            "summary": "????????",
            "sections": [{"title": "????", "body": ["????????"]}],
        },
    )

    result = run_renderer(
        "--bundle-dir",
        str(bundle_dir),
        "--content",
        str(content_path),
        "--no-pdf",
    )

    assert result.returncode == 2
    assert "suspected mojibake" in result.stderr
