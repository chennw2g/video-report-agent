# Project Plan

## Direction

The project is being rebuilt as `video-bundle-agent`, a small Python-first local tool.

The agent should collect source material from a video platform and write a local bundle that Codex can read.
It should not summarize the content itself.

The final user-facing workflow is a Codex plugin-shaped project with two skill responsibilities:

- `video-bundle-prep`: prepares reusable bundle evidence, classifies the video after reading text evidence,
  chooses a visual recall strategy, extracts frames, checks readiness, and writes mode-independent
  `report.input.json`.
- `video-report`: writes the final Chinese image-text report as HTML and preferred long PNG. PDF is optional
  compatibility output. It can call
  the prep workflow automatically when the user gives it a raw link or local video.

The bundle engine remains responsible for collection and frame extraction without LLM calls. AI remains
responsible for semantic classification, report-mode selection, and final report writing.

Do not create the plugin shell yet. Keep the project as two skills plus the Python CLI until the quick/deep
report structures and visual output design are stable, then package them into the plugin surface.

Report content structure is governed by `docs/report-output-contract.md`.
Report visual style is governed by `docs/report-visual-style.md`.
The v1 content structure is frozen as of 2026-06-07. The v1 visual baseline is Template D / `Editorial Lab`;
the next report-output phase is renderer implementation.

## Bundle Goals

Each bundle should contain:

- `manifest.json`: source URL, provider, timestamps, file list, and diagnostics summary.
- `metadata.json`: title, author, publish time, duration, platform ids, and source links.
- `transcript.segments.json`: normalized transcript segments when available.
- `transcript.txt`: plain text transcript when available.
- `transcript.alternatives.json`: optional transcript comparison index, especially for automatic subtitles.
- `transcript.comparison.json`: deterministic timestamp-window comparison between primary and alternative transcripts.
- `comments.json`: normalized comments when available.
- `danmaku.json`: optional normalized danmaku when explicitly requested.
- `slides.json`: screenshot/keyframe index.
- `content_profile.json`: Codex-authored video type tags and visual recall policy when the prep skill runs.
- `report.input.json`: compact evidence bridge for Codex report writing, generated after classification and
  visual evidence extraction. It is mode-independent.
- `report.content.draft.json`: renderer-compatible scaffold only, not final report analysis.
- `report.content.quick.json` / `report.zh.quick.html` / `report.zh.quick.png`: default quick report output.
- `report.content.deep.json` / `report.zh.deep.html` / `report.zh.deep.png`: explicit deep report output.
- `report.zh.quick.pdf` / `report.zh.deep.pdf`: optional compatibility exports only when useful.
- `screenshots/candidates/`: candidate screenshots extracted from the video.
- `screenshots/selected/`: later selected screenshots, when selection is implemented.
- `diagnostics.json`: explicit success, partial success, warning, and failure records.

## Design Principles

- Prefer explicit partial success over pretending a provider worked.
- Keep provider output raw enough for audit and normalized enough for downstream use.
- Keep secrets and cookies outside the repository.
- Make every generated bundle local and inspectable.
- Keep the first implementation small enough to reason about.
- Default to bounded fetches, especially for comments.
- Keep platform adapters behind provider boundaries so heavier crawlers can be added later.
- Treat visual recall as core evidence, not optional decoration.
- Do not write substantive reports unless transcript/transcription and screenshots/keyframes are available.
- Do not put semantic video-type classification in provider rules. The prep skill should classify after reading
  title, description, transcript/transcription, native source chapters, and user focus.
- Default final report mode is `quick`; use `deep` only when the user explicitly asks for `深入分析`,
  `深度报告`, `详细解读`, or `deep 模式`.
- `quick` audience feedback should stay brief. `deep` may cite representative comments with short
  original quotes; each cited comment should include `like_count` when available, and partial samples must
  be labelled as partial.
- Evidence attribution is mode-aware: `quick` uses lightweight timestamps, inline screenshots, comment
  like counts, and evidence-file lists; `deep` attributes key claims, disputed judgments, important data,
  and tutorial steps more explicitly.
- Both modes keep a final evidence index. `quick` lists key bundle files; `deep` may include used
  screenshots, transcript/comparison files, cited comment files, and relevant diagnostics.
- Reports may include a lightweight `注意事项` module near the end for source cautions, diagnostics, and
  report limits that materially affect interpretation, without dumping raw tool logs.
- Reports should distinguish source material from AI interpretation. AI-organized charts, tables,
  risk notes, and evaluations must not be presented as source claims.
- The AI multi-dimensional evaluation graphic is a first-glance orientation aid and should render as
  the first content module after the top basic/source information, before the video overview. Detailed
  rating reasoning remains in a later AI critique/detailed evaluation section.
- `quick` should not add AI-made visuals beyond the fixed multi-dimensional evaluation by default.
  `deep` may add labelled, evidence-traceable AI-organized visuals when they clarify the source.

## Phase 1 Scope

- Python project skeleton with `uv`.
- `doctor` command for required and optional local tools.
- Bundle schema and manifest writer.
- `yt-dlp` wrapper.
- `ffmpeg` / `ffprobe` wrapper.
- Visual recall modules:
  - `src/video_bundle_agent/media/frame_extractor.py`
  - `src/video_bundle_agent/media/visual_recall.py`
  - `src/video_bundle_agent/media/ocr.py`
- `ffprobe` video information reading: duration, frame rate, format, and stream basics.
- `ffmpeg` fixed-interval screenshot extraction.
- `screenshots/candidates/` output.
- `slides.json` output.
- `bundle.json` `slides_path` and `capabilities.has_slides`.
- YouTube basic provider for metadata, subtitles/transcript, audio transcription fallback, bounded comments,
  audience feedback, retained working video/audio, and optional visual recall.
- Staged frame extraction command for existing bundles.
- Bilibili API-first provider: `bilibili-api-python` for metadata, BV/AV/CID/page info, top-liked
  comments, optional danmaku, API playurl media download, retained working video/audio, transcription
  fallback, screenshots, and diagnostics; `yt-dlp` remains fallback only when API metadata or media fails.
- Xiaohongshu basic provider: URL/short-link resolution, explicit cookies, HTML note extraction,
  media URL normalization/download, video transcription, visual recall, and MediaCrawler-first bounded
  top-level comments. The bundled local signer is explicit fallback/debug only. Observed
  account/session risk responses such as `300011` are recorded as `PERMISSION_REQUIRED`; comments remain
  optional evidence and must not block the main content bundle.
- Local video provider skeleton.

## Implementation Order

1. Implement YouTube stage-1 collection: metadata, subtitles/transcript, bounded comments, audience feedback,
   a 1080p-or-best-available working video, whisper.cpp audio transcription fallback when subtitles are missing,
   whisper.cpp comparison transcripts when only automatic subtitles are available, and deterministic transcript
   comparison output for report-time inspection.
2. Let the Video Report Skill read stage-1 text evidence, classify the video, write `content_profile.json`, and choose
   the visual recall policy.
3. Implement staged visual recall through `extract-frames`: `ffprobe`, fixed/keyword/scene candidates, screenshots,
   and `slides.json`.
4. Implement `prepare-report` so the skill can read a compact `report.input.json` with selected screenshots,
   transcript windows, flagged transcript-comparison windows, audience feedback, evidence files, and limitations.
   This step runs after `content_profile.json` and `slides.json`; it does not replace full transcript reading.
5. Update YouTube smoke acceptance so transcript/transcription and slides are both required before report writing.
6. Validate Bilibili API-first online smoke and refine cookie/credential handling if public API access is insufficient.
7. Validate Xiaohongshu online smoke with MediaCrawler-first bounded comments. If comment APIs return
   platform risk-control responses, keep bundle creation moving and record diagnostics. Keep explicit
   signer tests only as fallback/debug coverage.
8. Keep MediaCrawler as an external bounded provider/reference for Xiaohongshu comments. Defer full
   MediaCrawler crawler workflows, search, author-homepage traversal, and nested feedback until the adapter
   boundary is clear.

## Visual Recall Module

The project must let Codex see video画面, not only transcript and comments.

Phase 1 implements `fixed_interval` extraction:

- Download a local video-only working file with a 1080p maximum target, using the best available lower resolution if 1080p is unavailable.
- Keep the working video under `raw/media/` by default for debugging and repeat frame extraction.
- Record the actual working-video resolution in metadata, slides metadata, or diagnostics.
- Use the local working video for `ffprobe` and `ffmpeg`; do not make online stream seeking the phase-1 default.

- `low`: one frame every 15 seconds.
- `medium`: one frame every 5 seconds.
- `high`: one frame every 2 seconds.

The default one-step visual recall level is `medium`:

```text
--visual-recall none|low|medium|high
```

For skill-led reports, use `--visual-recall none` during initial `analyze` so Codex can read text evidence first,
classify the video, and then call `extract-frames` with a selected policy.

The separate strategy switch is:

```text
--visual-strategy auto|fixed|keyword|scene|all
```

Strategy behavior:

- `fixed`: fixed-interval frames only.
- `keyword`: fixed-interval frames plus transcript keyword trigger frames.
- `scene`: fixed-interval frames plus ffmpeg scene-change frames.
- `all`: fixed-interval, keyword-trigger, and scene-change frames.
- `auto`: `low` uses fixed only, `medium` uses fixed plus keyword trigger, and `high` uses fixed plus keyword trigger plus scene-change detection.

This keeps the default `medium` run faster while still adding useful frames around transcript cues.
Scene detection is more expensive because ffmpeg scans the video, so it is reserved for `high` or explicit strategy requests.

Candidate screenshot collection prioritizes complete visual coverage. The default candidate cap is `0`,
meaning no cap. This lets dense tutorial, software demo, chart, and news videos preserve full fixed-interval
coverage in `screenshots/candidates/`.

A positive `--max-screenshots` or `--max-candidate-screenshots` value is an explicit performance/storage limit.
If interval extraction exceeds that positive cap, sample timestamps evenly across the video, record the
sampling/cap information in `slides.json.extraction`, and emit a `VISUAL_COVERAGE_TRUNCATED` diagnostic.
The cap applies to the combined candidate set after fixed, keyword, and scene candidates are merged.

Report image volume is controlled separately by `select-evidence` and `prepare-report --max-images`.
The skill should keep report inputs selective while letting the bundle retain broad candidate coverage.

Screenshots are written to:

```text
outputs/<source_id>/
├─ screenshots/
│  ├─ candidates/
│  └─ selected/
├─ slides.json
```

Screenshot names encode timestamp and extraction reason:

```text
000012.5s_fixed.png
000042.0s_scene.png
000118.2s_keyword.png
```

Use `ffmpeg` frame extraction:

```text
ffmpeg -ss <seconds> -i <video_file> -frames:v 1 -q:v 1 <output.png>
```

The prep skill chooses visual recall by semantic judgment. Common labels include `访谈`, `单人播客`, `新闻`,
`教程`, `深度分析`, `产品介绍`, `会议`, `演讲`, `脱口秀`, `软件演示`, `财经分析`, and `课程`.

Low visual-density videos such as solo podcasts and interviews usually use low/fixed. High visual-density videos
such as tutorials, news, software demos, finance charts, and data-rich analysis usually use high/all. Treat this as
guidance, not an automatic rule table.

Current visual recall can combine fixed interval, transcript keyword triggers, and ffmpeg scene-change detection.
Future work should improve their scoring, deduplication, and selection rather than moving semantic classification
into provider rules.

Phase 2 still defers:

- OCR through tesseract, PaddleOCR, or another local OCR tool.
- screenshot selection, deduplication, sharpness scoring, and brightness scoring.

Keyword trigger seed terms:

```text
这里, 看这里, 点击, 设置, 报错, 结果, 数据, 风险, 对比, 第一步, 第二步, 接下来, 注意, 关键
估值, PE, PB, ROE, 利润, 营收, 现金流, 涨幅, 跌幅, 回撤, 仓位, 买入, 卖出, 支撑位, 压力位, 财报
```

Current implementation uses this UTF-8 keyword set:

```text
这里, 看这里, 点击, 设置, 报错, 结果, 数据, 风险, 对比, 第一步, 第二步, 接下来, 注意, 关键
估值, PE, PB, ROE, 利润, 营收, 现金流, 涨幅, 跌幅, 回撤, 仓位, 买入, 卖出, 支撑位, 压力位, 财报
```

## Deferred

- LLM summaries.
- Ranking or scoring content quality.
- UI.
- Long-term daemon/service mode.
- Multi-platform orchestration.
- Batch crawling.
- Bypassing platform controls, captchas, paywalls, DRM, or login requirements.
- Automated selected screenshot copying into `screenshots/selected/`.
- OCR as a blocking requirement.
- Complex screenshot deduplication or visual scoring.
