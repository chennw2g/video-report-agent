---
name: video-bundle-prep
description: Use when an agent needs to prepare a video evidence bundle from a video URL, local video file, or existing bundle before report writing; handles provider workflow selection, stage-1 collection, semantic video classification, visual policy, frame extraction, readiness checks, and mode-independent report.input.json generation.
---

# Video Bundle Prep

Prepare source evidence only. Do not write the final user-facing report.

This skill turns a video link, local video file, or existing bundle into a reusable evidence bundle with `content_profile.json`, `slides.json`, readiness diagnostics, selected evidence, and mode-independent `report.input.json`.

## Workflow

1. Identify the input:
   - Video URL or local file: create a fresh bundle by default.
   - Existing bundle directory: reuse it and do not refresh source material unless the user explicitly asks.
2. For fresh URL/file inputs, choose the provider workflow by platform:
   - YouTube: yt-dlp-first.
   - Bilibili: Bilibili API-first; yt-dlp is fallback only.
   - Xiaohongshu: lightweight metadata/media provider plus MediaCrawler-only bounded comments.
   - Local video: local media workflow.
3. Run stage-1 collection with transcript/transcription evidence, bounded comments when requested, retained working media, no screenshots yet, and no LLM calls.
4. Read `manifest.json`, `diagnostics.json`, `metadata.json`, and transcript/transcription evidence.
5. If transcript/transcription is missing, inspect diagnostics and report whether the source is invalid or the tool/provider failed. Do not continue to report preparation.
6. Classify the video semantically from title, description, native source chapters, transcript, and user focus. Do not use keyword-count rules as the classifier.
7. When the provider exposes native chapters, write them to `source_chapters.json` and record
   `source_chapters_path` in `bundle.json`; Bilibili `metadata.pages` is only pages/parts, not progress-bar chapters.
   Current native chapter sources are Bilibili player `view_points` and YouTube yt-dlp `chapters`.
   Xiaohongshu currently has no reliable native chapter source, so use natural sections later in report writing.
8. Write `<bundle-dir>/content_profile.json` with `primary_type`, `type_tags`, rationale, and selected visual policy.
9. Write `<bundle-dir>/visual_selection_plan.json` with semantic anchors, dynamic terms, time hints, and
   per-anchor `need_screenshot` decisions. The agent decides what visual evidence matters; the tool only
   matches those pointers against transcript timestamps and candidate screenshots.
10. Run `video-bundle-agent extract-frames <bundle-dir>` using the visual policy.
11. Run `video-bundle-agent check-bundle <bundle-dir>`.
12. If `report_ready` is false, report blockers and repair steps instead of preparing final report inputs.
13. Run `video-bundle-agent select-evidence <bundle-dir> --plan visual_selection_plan.json`.
14. Run `video-bundle-agent prepare-report <bundle-dir> --plan visual_selection_plan.json` to write
   mode-independent `report.input.json`.
15. Return the bundle path, readiness status, important diagnostics, and generated artifact paths.

## Mode Boundary

- Ignore `quick` and `deep` report modes during bundle preparation.
- A bundle is a reusable evidence library. It should support a quick report now and a deep report later without recollecting the same source.
- `report.input.json` is also mode-independent. It is an evidence index, not a quick/deep-specific final report input.
- Report mode belongs to `video-report`.

## Commands

For YouTube:

```powershell
uv run video-bundle-agent analyze "<url>" `
  --out outputs/<safe-name> `
  --comments `
  --max-comments 100 `
  --visual-recall none `
  --cookies "$env:APPDATA\video-bundle-agent\youtube.cookies.txt" `
  --no-llm
```

For Xiaohongshu, run the platform analyze command. Comments are collected only through the managed
MediaCrawler checkout, using MediaCrawler's official `xhs detail` jsonl workflow and saved browser profile.
The first run may open a browser for QR/SMS login; later runs should reuse MediaCrawler's saved profile.
MediaCrawler detail runs are bounded by the provider timeout, currently 180 seconds; if it times out, report
login, verification, or platform blocking diagnostics instead of waiting silently.
Pass explicit cookies only when needed for note HTML/media access:

```powershell
uv run video-bundle-agent analyze "<url>" `
  --out outputs/<safe-name> `
  --comments `
  --max-comments 100 `
  --visual-recall none `
  --no-llm
```

Add this only when the note HTML/media request needs an exported Xiaohongshu cookie file:

```powershell
--cookies "$env:APPDATA\video-bundle-agent\xiaohongshu.cookies.txt"
```

Do not start the old dedicated `9231` CDP browser path for normal Xiaohongshu runs. Do not use `xhs-signer`,
`--xhs-sign-url`, or `XHS_SIGN_URL`; that local signer path is no longer supported.

After classification:

```powershell
uv run video-bundle-agent extract-frames outputs/<safe-name> `
  --visual-recall <low|medium|high> `
  --visual-strategy <auto|fixed|keyword|scene|all> `
  --max-candidate-screenshots 0

uv run video-bundle-agent check-bundle outputs/<safe-name>
uv run video-bundle-agent select-evidence outputs/<safe-name> --max-images 12 --plan visual_selection_plan.json
uv run video-bundle-agent prepare-report outputs/<safe-name> --max-images 12 --plan visual_selection_plan.json
```

`--max-candidate-screenshots 0` means no candidate cap. Keep candidate visual coverage complete; report rendering can choose fewer images later.

## Classification

Use common labels when they fit: `访谈`, `单人播客`, `新闻`, `教程`, `深度分析`, `产品介绍`, `会议`, `演讲`, `脱口秀`, `软件演示`, `财经分析`, `课程`, `其他`.

Suggested visual policy:

- Low visual density, such as solo podcast, interview, talk show: `visual_recall=low`, `visual_strategy=fixed`.
- Medium visual density, such as speech, lecture, meeting, product intro: `visual_recall=medium`, `visual_strategy=auto`.
- High visual density, such as news, tutorial, software demo, finance charts, data-rich deep analysis: `visual_recall=high`, `visual_strategy=all`, `max_screenshots=0`.

Write:

```json
{
  "schema_version": "0.1.0",
  "primary_type": "教程",
  "type_tags": ["教程", "软件演示"],
  "rationale": "The transcript repeatedly explains on-screen steps and UI operations.",
  "visual_policy": {
    "visual_recall": "high",
    "visual_strategy": "all",
    "max_screenshots": 0,
    "reason": "The report needs complete candidate coverage around UI changes and transcript cues."
  }
}
```

## Visual Selection Plan

After writing `content_profile.json` and before `select-evidence`, write `visual_selection_plan.json`.
Use the transcript, native source chapters, content type, comments when relevant, and user focus to name the
moments where screenshots may be useful.

Do not create a generic keyword list only. The anchors should reflect this specific video: result screens,
tool settings, chart changes, visual comparisons, chapter transitions, data tables, UI states, examples, or
other moments where image evidence improves understanding.

For low-visual-variation videos such as pure talking-head, solo podcast, or interview, set
`body_screenshot_policy` to `selective` and mark most anchors as `need_screenshot=false`; keep only a hero or
rare visually distinct moment if it helps.

Recommended shape:

```json
{
  "schema_version": "0.1.0",
  "source_type": "tutorial",
  "visual_density": "high",
  "body_screenshot_policy": "selective",
  "semantic_anchors": [
    {
      "id": "anchor_0001",
      "label": "Final result screen",
      "terms": ["result", "final output"],
      "time_hints": ["03:20-03:45"],
      "need_screenshot": true,
      "reason": "The result must be visually checked.",
      "body_placement": "core_points"
    }
  ]
}
```

Then pass it to both evidence commands:

```powershell
uv run video-bundle-agent select-evidence outputs/<safe-name> --max-images 12 --plan visual_selection_plan.json
uv run video-bundle-agent prepare-report outputs/<safe-name> --max-images 12 --plan visual_selection_plan.json
```

## Evidence Gate

- Minimum report preparation evidence is transcript or audio transcription plus screenshots/keyframes.
- Comments are optional. Mark missing or blocked audience feedback in diagnostics.
- Do not invent missing transcript, screenshots, comments, danmaku, or OCR.
- Do not bypass the bundle engine to directly scrape around missing core evidence.
- For Xiaohongshu `PERMISSION_REQUIRED`, `COOKIE_REQUIRED`, CAPTCHA, or account-risk diagnostics, keep metadata/media/transcription/screenshots moving and mark comments as limited.
