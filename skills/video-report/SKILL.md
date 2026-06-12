---
name: video-report
description: Use when AI needs to generate a final Chinese HTML/long-PNG report from a prepared video-bundle-agent bundle or report.input.json; also use when the user gives a video URL/local video and wants a report, in which case first run the video-bundle-prep workflow, then write quick or deep report output.
---

# Video Report

Write the final user-facing report from prepared video evidence. The report is Chinese by default and outputs HTML plus a long-image PNG. PDF is optional compatibility output when explicitly useful.

Use `video-bundle-prep` for evidence preparation. This skill may invoke that workflow automatically when the user gives a raw video URL or local file.

Report content structure v1.1 is frozen as of 2026-06-08. The accepted visual baseline is Template D
(`Editorial Lab`): light blue-green, left-navigation, evidence-first research brief. Follow the content and
visual contracts unless the user explicitly reopens them; renderer implementation may still evolve.

## Mode Selection

- Default mode is `quick`.
- Use `deep` only when the user explicitly asks with a clear trigger: `深入分析`, `深度报告`, `详细解读`, or `deep 模式`.
- Do not auto-upgrade to `deep` because the video looks dense or tutorial-like.
- If a `quick` run reveals that the source is suitable for deeper study, mention that `deep` mode is available.

Mode boundaries:

- `quick`: fast understanding, full chapter/section coverage inside the video overview, concise points,
  short AI critique, and a few key images only when they materially improve understanding.
- `deep`: learning/research report with richer analysis and more visual evidence. Adapt the output to
  the source type: tutorial/course/software videos become readable text tutorials; news/interview/analysis
  videos become deeper content and viewpoint analysis.
- Both modes share the same HTML/PNG design system. PDF is optional compatibility output. They differ in depth and evidence density, not output format.

## Workflow

1. Identify the input:
   - URL or local video: run the `video-bundle-prep` workflow first.
   - Existing bundle directory: reuse it.
   - `report.input.json`: use its containing bundle directory.
2. For an existing bundle, perform a light check:
   - Read `bundle.json` and `diagnostics.json`.
   - Run `video-bundle-agent check-bundle <bundle-dir>`.
   - Regenerate `report.input.json` only if it is missing or stale relative to `bundle.json`, `slides.json`, or `content_profile.json`.
   - Do not redownload media, refetch comments, or rerun frame extraction unless the user explicitly asks to refresh source material.
3. If `report_ready` is false, report blockers and concrete repair steps instead of writing a substantive report.
4. Read `report.input.json` first as the evidence index.
5. Read the full transcript through `transcript.txt` or `transcript.segments.json` before writing `report.content.<mode>.json`.
6. Inspect selected screenshots from `report.input.json.selected_evidence.selected_images`. Do not read every screenshot candidate by default.
7. If `transcript.comparison.json` exists, inspect flagged windows before trusting technical terms, names, numbers, or key claims.
8. Read metadata, comments, optional danmaku, slides, and `content_profile.json` as needed.
   - If `source_chapters.json` exists or `report.input.json.source_chapters.available` is true, use those
     native source chapters as the report's chapter/content-map basis.
   - If native source chapters are unavailable, infer natural sections from the transcript and visual evidence,
     and do not treat Bilibili `metadata.pages` as progress-bar chapters. YouTube `source_chapters.json`
     comes from yt-dlp `chapters`; Xiaohongshu usually has no native chapter source and should use natural
     sections.
9. Clearly separate observed source material from AI inference.
10. Write mode-specific content JSON.
11. Render mode-specific HTML/PNG with `scripts/render_report.py`; produce PDF only when explicitly useful.

## Output Files

For `quick`:

```text
report.content.quick.json
report.zh.quick.html
report.zh.quick.png
```

For `deep`:

```text
report.content.deep.json
report.zh.deep.html
report.zh.deep.png
```

When the user does not specify a mode, default to `quick`. The latest/default quick report may also write compatibility aliases:

```text
report.content.json
report.zh.html
report.zh.png
```

Render with:

```powershell
python .\skills\video-report\scripts\render_report.py `
  --bundle-dir outputs\<bundle-dir> `
  --content outputs\<bundle-dir>\report.content.<mode>.json `
  --html outputs\<bundle-dir>\report.zh.<mode>.html `
  --no-pdf `
  --png outputs\<bundle-dir>\report.zh.<mode>.png
```

The renderer should capture only the main report body, hide the left navigation, and preserve the HTML body
layout for PNG. If PDF is explicitly requested, pass `--pdf`; if PDF export fails, keep HTML/PNG and state the
PDF blocker.

## Visual Style

Use Template D / `Editorial Lab` as the default visual template unless the user explicitly asks to redesign
the report.

This section is visual-only. Do not use it to decide report section order, wording, rating placement,
comment rules, label text, or content depth. Those rules belong to the content contract sections below and
`docs/report-output-contract.md`.

- Overall feel: light Chinese research brief, restrained and readable, not a landing page and not a dense
  dashboard.
- Color: light cool-gray page background, white content panels, dark blue-gray left navigation, blue-green
  primary accent, deep green secondary accent, muted amber auxiliary status token, and muted rose/red warning
  status token.
- Layout: desktop uses left navigation plus a wide main reading column. The top visual area uses a stable
  two-column hero with text/metadata on one side and a representative thumbnail/frame on the other. Keep
  normal horizontal or near-horizontal images at their original aspect ratio, with no decorative frame, and
  center them against the text block. For portrait/vertical video frames in the hero, use a stable 3:2
  horizontal contain box with side whitespace so the title area is not stretched by a tall vertical image.
  Body modules stack vertically as full-width panels.
- Typography: use readable Chinese sans-serif typography, generous line height, no viewport-scaled font
  sizes, and default letter spacing.
- Panels/cards: use white surfaces, low-contrast borders, light shadows, and 8px-or-smaller radii. Avoid
  nested page-section cards.
- Screenshots/media: use bordered image cards with a lower-emphasis caption area. Preserve screenshot
  readability and avoid decorative filters.
- Charts/tables: use simple radar charts, clean tables, and restrained generated visual components that
  match the same card style.
- Badges/status: badges may visually distinguish information roles with stable color tokens, but the exact
  badge text and role taxonomy come from the content contract and report content, not from this visual style.
- Header text discipline: write the title, tags, and metric values so the default desktop hero stays compact.
  Target at most two visual lines for the title, a short single row of tags on desktop, and metric values that
  can fit naturally without truncation. The renderer may auto-reduce title and metric font sizes to fit, but
  it must not hide key text with clipping or ellipses. Prefer shorter wording plus smaller fixed font classes
  over hidden text.
- Header metric cards keep labels such as `平台`, `频道`, and `发布时间` anchored in the bottom label area.
  Auto-shrinking the metric value must not move the label line out of alignment with neighboring cards.
- PDF/mobile: hide or collapse navigation when needed and preserve readable single-column body flow.
- Long PNG export: hide the left navigation and capture only the main report body.
- Footer signature: keep a small bottom signature in the form
  `Generated by <agent> (Powered by <model>)`. The agent is the execution agent/shell, such as `CODEX`
  or `Claude Code`, not the report project name. This is report provenance, not evidence commentary.
- Static visual reference: `outputs/report-style-variants/deep-template-d-editorial-lab-score-first.html`.
  This file is only a style reference; do not copy its sample text, scores, comments, or screenshots into
  real reports.

## Minimum Evidence Gate

- Do not write a substantive report from metadata or comments alone.
- Require transcript or audio transcription plus screenshots, slides, or keyframes.
- Comments are optional. If unavailable, mark audience feedback as missing or limited.
- If transcript/transcription or screenshots/keyframes are missing, inspect `diagnostics.json`.
- If the source link/file is invalid, say so.
- If the local toolchain or provider failed, explain the likely cause, propose the repair, and retry after the fix before writing the report.
- Do not directly scrape around the bundle engine to fill missing core evidence.

## Content Contract

After reading `report.input.json`, the full transcript, and selected evidence, create `<bundle-dir>/report.content.<mode>.json`.

Use this shape; omit only sections that are genuinely unavailable:

```json
{
  "report_mode": "quick",
  "title": "",
  "signature_agent": "CODEX",
  "signature_model": "GPT-5 Codex",
  "eyebrow": "platform · report mode · source type · date",
  "summary": "",
  "conclusion": "",
  "tags": [],
  "metrics": [{"label": "", "value": ""}],
  "evaluation": {
    "scale": {"min": 1, "max": 5},
    "dimensions": [
      {"key": "credibility", "label": "可信度", "score": 0},
      {"key": "originality", "label": "原创性", "score": 0},
      {"key": "value_density", "label": "价值密度", "score": 0},
      {"key": "argument_strength", "label": "论证强度", "score": 0},
      {"key": "information_density", "label": "信息密度", "score": 0},
      {"key": "timeliness", "label": "时效性", "score": 0}
    ],
    "commentary": []
  },
  "visual_evidence": [
    {"image_path": "screenshots/candidates/example.png", "title": "", "caption": ""}
  ],
  "timeline": [
    {"time": "00:00", "topic": "", "summary": "", "evidence": ""}
  ],
  "sections": [{"title": "", "body": [""], "visual_evidence": []}],
  "section_labels": {
    "video_content": "视频内容",
    "codex_analysis": "AI 解读",
    "audience_feedback": "观众反馈",
    "diagnostic_note": "诊断提示"
  },
  "audience_feedback": [
    {
      "title": "",
      "body": [""],
      "representative_comments": [
        {"text": "", "like_count": 0, "reply_count": 0, "source_id": ""}
      ]
    }
  ],
  "diagnostic_notes": [
    {"severity": "warning", "title": "", "body": [""], "evidence": ""}
  ],
  "attention_notes": [
    {"severity": "warning", "title": "", "body": [""], "evidence": ""}
  ],
  "codex_visuals": [
    {
      "type": "flowchart",
      "title": "",
      "label": "AI 整理",
      "basis": ["transcript:12:34", "screenshots/candidates/example.png"],
      "data": {}
    }
  ],
  "recommendations": [""],
  "project_notes": [""],
  "evidence_files": [{"path": "metadata.json", "purpose": ""}],
  "limitations": [""]
}
```

`report.content.draft.json` is only a scaffold from the bundle engine. Do not treat it as final.

## Quick Structure

Use this structure for `quick` unless the user asks otherwise:

1. Basic information: title, author, platform, publish time, duration, link, and video type tags.
   Include view count and like count when available.
2. AI multi-dimensional evaluation snapshot: render the compact rating visual before the video overview
   so the reader sees the overall AI judgment immediately. Label it as AI evaluation. Do not put
   per-dimension reasoning beside the chart.
3. Video overview: briefly describe what the video covers and include the complete source chapters or
   inferred section structure. Keep this section mostly objective; move judgments, learning value, and
   applicability comments to AI critique. Do not force this into one sentence.
   Use a cover/thumbnail as the main visual when available and useful.
4. Core points: 3-7 important points. Embed timestamp screenshots next to the specific point they support
   instead of creating a standalone image gallery.
5. AI critique: briefly explain the most important rating judgments and source limits.
   Default dimensions: credibility, originality, value density, argument strength, information density,
   and timeliness.
   Use a 1-5 scale. Do not use percentages or 0-10 scores by default.
6. Audience feedback: brief and explicit about missing comments.
7. Attention notes and evidence files. Merge source cautions, diagnostics, and limitations into
   attention notes. Do not mention screenshot coverage unless visual evidence is missing, failed, or
   materially incomplete.

## Deep Structure

Use this structure for `deep` unless the user asks otherwise:

1. Basic information and source context.
2. AI multi-dimensional evaluation snapshot: render the compact rating visual before the video overview.
   Keep detailed rating reasoning for the later AI critique section.
3. Video overview and content map.
4. Original chapter-by-chapter or natural-section detail.
5. Core viewpoint deep dive.
6. Audience feedback and visible disagreement, if comments are available.
7. AI-organized visuals, diagrams, timelines, matrices, or tables when they clarify the material.
8. AI detailed evaluation and critique using the same rating dimensions as `quick`.
9. Attention notes: merge source cautions, tool diagnostics, and report limitations near the end.
10. Evidence index.

## Audience Feedback

- In `quick`, summarize 2-4 main feedback directions when comments are available. Mention obvious
  controversy or common questions if present. If comments are missing, say so briefly.
- In `deep`, group feedback into useful buckets such as support, criticism, questions, supplemental
  information, and disputes.
- When `deep` cites a representative comment viewpoint, a short original quote is allowed when it preserves
  useful audience voice. Include the comment's `like_count` when available. Include `reply_count` when it
  helps show disagreement or discussion intensity.
- Representative comments must be traceable to real items in `comments.json`. Do not invent placeholder
  comments. If a cited comment has missing or zero likes, do not present it as a high-like representative
  comment unless the source sample itself proves that value.
- Do not dump large raw comment lists. If the sample is small or partial, say so explicitly and do not
  present it as the whole audience view.

## Evidence Attribution

- In `quick`, keep evidence attribution lightweight: timestamps, inline screenshots, comment `like_count`,
  and the final evidence-file list are enough.
- In `deep`, attribute key claims, disputed judgments, important data, and tutorial steps more explicitly.
- Evidence forms include transcript timestamps, inline screenshots, short comment quotes with `like_count`,
  and the evidence index.
- Do not cite every sentence. Important conclusions must be traceable to bundle evidence.
- Keep normal prose readable; avoid paper-style footnote clutter unless the user asks for that style.

## Source vs AI Interpretation

- Distinguish source material from AI interpretation.
- Source material includes video overview, chapter details, source claims, transcript-backed points, and
  factual visual descriptions.
- AI interpretation includes evaluation, risk notes, viewpoint analysis, applicability judgments, and
  AI-organized tables, charts, or diagrams.
- Audience feedback and diagnostic/trust notes should also be distinguishable from source content.
- Use lightweight labels when useful: `视频内容`, `AI 解读`, `观众反馈`, and `诊断提示`.
- Do not label every sentence. The goal is to prevent AI inference from being mistaken for the
  original author's claim.

## AI-Organized Visuals

- In `quick`, do not add AI-made charts beyond the fixed multi-dimensional evaluation by default.
- In `deep`, AI-organized tables, diagrams, flowcharts, comparison charts, matrices, or timelines are
  allowed when they clarify the source.
- They must be useful, not decorative.
- Do not force AI-organized visuals into tables. Choose the form that fits the content: process flow,
  timeline, matrix, comparison table, axis chart, or concise diagram.
- Label them as `AI 整理` or `AI 解读`.
- Do not present them as original video screenshots or author-provided charts.
- Keep their basis traceable to transcript timestamps, sections, screenshots, or other bundle evidence.
- Good deep candidates include tutorial step flowcharts, concept maps, viewpoint comparison tables,
  risk/benefit matrices, and event timelines.

## Evidence Index

- Keep an evidence index at the end of both modes.
- In `quick`, list key bundle files only, such as `metadata.json`, `transcript.txt`,
  `transcript.segments.json`, `slides.json`, `comments.json`, `audience_feedback.json`, and
  `diagnostics.json` when present.
- In `deep`, the index may include used screenshots, transcript/comparison files, cited comment files,
  and diagnostics that affect interpretation.
- The evidence index is for audit and follow-up inspection. Do not overload the body with file-path
  references.

## Attention Notes

- Both modes may include a lightweight `注意事项` module near the end.
- Do not dump raw tool logs.
- Include only diagnostics that materially affect interpretation, such as transcript disagreement, missing
  or partial comments, missing visual evidence, OCR absence for screen-text-heavy videos, or platform
  permission/risk-control diagnostics.
- Blocking issues should stop substantive report writing and produce repair steps instead.
- Non-blocking issues should stay concise.
- Final reports should render these together as `注意事项` rather than scattering separate diagnostics,
  risks, and limitations modules.

Source-type adaptation:

- For tutorials, courses, software demos, and process-heavy videos, reconstruct the source into a readable
  text tutorial with concepts, steps, prerequisites, pitfalls, examples, and important screen states.
- For news, interviews, speeches, analysis, opinion, and market commentary, focus on claims, assumptions,
  evidence, context, implications, disagreements, and risks.
- Embed screenshots inside the relevant chapter/detail/core-viewpoint discussion. Do not create a standalone
  key-image section unless the user asks for an image appendix.
- Do not place a screenshot in every chapter or viewpoint by default. Include an image only when it adds
  information that the text alone does not convey, such as an interface state, visual comparison, prompt
  table, timeline, chart, or screen-specific operation.
- For talking-head, podcast, interview, and other low-visual-variation videos, do not embed body screenshots
  by default. If a frame only repeats burned-in subtitles or shows the same speaker pose, keep it as bundle
  evidence or a hero representative image, not as filler beside analysis text.
- Avoid repeated or near-identical screenshots in adjacent sections. When two screenshots are genuinely
  useful in the same block, render them compactly side by side when the viewport allows it.
- Do not reuse the same screenshot in both the overview and a later core/chapter section. Keep it where it
  best supports the text.
- Do not add a standalone "适用人群" section by default. Applicability can appear as a small point inside
  the analysis when useful.
- Do not add generic "学习笔记" or "可执行清单" sections by default. Add checklists only when the source
  itself is procedural or the user explicitly asks for action items.
- Use AI-organized tables, process charts, or comparison diagrams when they clarify the material; label
  them as AI-organized.
