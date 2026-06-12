# Development Rules

These rules keep `video-bundle-agent` focused on producing reliable, inspectable source bundles.

## Status Snapshot Discipline

- Treat `docs/current-status.md` as the context-compaction handoff file.
- After every material project change, update `docs/current-status.md` before final reporting or committing
  when the change affects capabilities, provider state, report contracts, validation status, known blockers,
  external tool state, or recommended next steps.
- Material changes include provider behavior, report structure, visual rules, skill workflow, CLI commands,
  dependency/tool status, smoke-test results, Git baseline changes, and any paused/resumed platform workflow.
- If a change is purely mechanical and does not affect the status snapshot, explicitly say so in the final
  response instead of silently skipping the file.
- Before creating a commit, check whether `docs/current-status.md` needs an update alongside the changed code,
  docs, tests, and skills.

## Product Boundary

- The user-facing target is a Codex plugin-shaped workflow: link or local file in, prepared bundle evidence,
  then final report out.
- The Python bundle engine collects source material and writes bundles.
- The Python bundle engine does not generate final reports and does not call LLMs.
- The Python bundle engine may prepare report input scaffolds from bundle evidence, but these are not
  substantive analysis and must not replace Codex-written final reports.
- The workflow is split into two skill responsibilities:
  - `video-bundle-prep` prepares evidence, classifies the video, chooses visual policy, extracts frames,
    checks readiness, and writes `report.input.json`.
  - `video-report` writes the final user-facing report from a prepared bundle or `report.input.json`.
- `video-report` may invoke the `video-bundle-prep` workflow automatically when the user gives it a raw
  video link or local video file, but report writing remains separate from evidence preparation.
- Semantic video-type classification belongs in Codex, not in provider keyword rules.
- Report generation belongs in Codex after bundle creation, using bundle files and diagnostics as evidence.
- The eventual project packaging surface is a Codex plugin that contains both skills, shared documentation,
  helper scripts, and the local bundle engine entrypoints. It should not collapse provider collection,
  evidence preparation, and final report writing into one opaque step.
- Defer the plugin shell/manifest until quick/deep report structure and visual output design are stable.
  For now, maintain the two skills and Python CLI directly.

## Phase 1 Acceptance

- Phase 1 is accepted when the bundle pipeline is stable, diagnosable, and usable for YouTube.
- YouTube should produce metadata, transcript/subtitles or audio transcription, screenshots/keyframes, bounded comments, audience feedback, diagnostics, bundle index, and manifest.
- Visual recall is a phase-1 requirement for report-skill readiness.
- Bilibili uses a Bilibili workflow directly: `bilibili-api-python` is primary for BV/AV/CID/page
  metadata, bounded top-liked comments, optional danmaku, and API playurl media download; `yt-dlp`
  is fallback only when API metadata or media fails.
- Xiaohongshu uses a lightweight provider boundary first: explicit cookies, HTML note extraction,
  media URL normalization/download, local video transcription, visual recall, and MediaCrawler-only bounded
  top-level comments. MediaCrawler is a managed external runtime for Xiaohongshu comments, not a vendored
  Python package inside `src/`.
- Local video may remain a skeleton until ffprobe, transcription, OCR, and frame extraction are deliberately scoped.
- The phase-1 skill may be minimal, but its intended workflow is to call the bundle engine from a user-supplied link or file and then produce a report from the bundle.

## Implementation Order

- Implement YouTube stage-1 collection with retained working video before expanding real Bilibili or Xiaohongshu provider depth.
- Make the Video Report Skill classify stage-1 text evidence and call staged frame extraction.
- Update YouTube smoke acceptance to require transcript/transcription and slides before report writing.
- Add `prepare-report` as the bridge from normalized bundle evidence to Codex report writing input.
- After the report evidence gate works, validate Bilibili API-first online smoke, then proceed to
  Xiaohongshu adapter research/integration.

## Credentials And Platform Boundaries

- Cookies and login state are allowed only as explicit local inputs for user-controlled runs.
- The stable YouTube cookies file path is `%APPDATA%\video-bundle-agent\youtube.cookies.txt`.
- The stable Bilibili cookies file path is `%APPDATA%\video-bundle-agent\bilibili.cookies.txt`.
- The stable Xiaohongshu cookies file path is `%APPDATA%\video-bundle-agent\xiaohongshu.cookies.txt`.
- Xiaohongshu comments use MediaCrawler's own saved browser profile under its checkout
  (`browser_data/cdp_xhs_user_data_dir`). Do not require the user to manually start the old dedicated
  `9231` CDP browser path for normal runs.
- MediaCrawler official `xhs detail` runs should be bounded. The current provider timeout is 180 seconds;
  if a run waits longer than that, treat it as login, verification, or platform blocking instead of leaving
  the user waiting for a long silent browser session.
- Bilibili authenticated pagination should use an explicit Bilibili Netscape cookies file with
  `--cookies`; `--cookies-from-browser` is only a yt-dlp fallback input and does not authenticate
  `bilibili-api-python`.
- Do not commit cookies, tokens, API keys, exported browser state, or account databases.
- Do not read cookies by default; require `--cookies` or another explicit option.
- Bundle manifests and diagnostics may record the local cookies path for reproducibility, but must not include cookie contents.
- Do not bypass captchas, paywalls, DRM, platform account restrictions, or rate-limit controls.
- Do not implement bulk crawling or account-rotation workflows in phase 1.

## External Tool Invocation

- When invoking an external project or tool with a different working directory, pass project output
  directories as resolved absolute paths.
- Do not pass repo-relative output paths to external checkouts such as MediaCrawler, because they will be
  resolved relative to the external tool's `cwd` and can silently write files outside the bundle directory.
- Bundle indexes may still store normalized relative paths for user-facing artifacts; the absolute-path rule
  applies to subprocess invocation boundaries.

## Audience Feedback Rules

- Default comment collection is top 100 by `like_count` descending for every platform that supports
  comment like counts.
- Do not default to all comments, all replies, or full historical audience feedback.
- Bilibili comments, Xiaohongshu comments, and nested replies must have explicit limits before implementation.
- Xiaohongshu comments use the local MediaCrawler checkout as the only supported collection path. It must
  call MediaCrawler's official `xhs detail` workflow, request bounded top-level comments, save `jsonl`
  output under `raw/xiaohongshu/mediacrawler/`, and normalize comments by `like_count`.
- Do not reintroduce the old bundled local signer, external signing service, `xhs-signer`, `--xhs-sign-url`,
  or `XHS_SIGN_URL` flow unless a new ADR explicitly replaces the MediaCrawler-only decision.
- Xiaohongshu account/session risk and interactive verification responses, including observed `300011`
  responses, are `PERMISSION_REQUIRED` diagnostics. They are not blockers for metadata, media,
  transcription, screenshots, or the main content report.
- Xiaohongshu login-expired responses, including observed `-100` responses, are `COOKIE_REQUIRED`
  diagnostics. Do not keep repeating QR/SMS login loops as the default response once the provider has
  captured the platform error clearly.
- If Bilibili returns fewer comments than requested, record the partial count and a warning diagnostic;
  do not silently label a 3-item anonymous sample as top 100.
- If Xiaohongshu or MediaCrawler returns fewer comments than requested, record the partial count and do not
  imply that a small recovered sample is the complete top 100.
- Bilibili danmaku is disabled by default; the current default is `--max-danmaku 0`.
- If danmaku is explicitly enabled, it must be represented separately from comments and must record
  whether it is complete or sampled.
- `audience_feedback.json` should contain lightweight counts, top items, and simple rule-based buckets only in phase 1.
- Do not use LLMs or opaque sentiment classifiers when building `audience_feedback.json` in the core program.
- Record `count_fetched` and any known provider-side total separately; never imply partial samples are complete.
- `quick` reports should summarize audience feedback briefly: 2-4 main feedback directions when comments
  are available, obvious controversy or questions if present, and a one-line missing/limited note when
  comments are unavailable.
- `deep` reports may analyze audience feedback more fully: support, criticism, questions, supplemental
  information, and disputes. When citing a representative comment viewpoint, a short original quote is
  allowed when it preserves useful audience voice. Include the comment's `like_count` when available so
  the reader can see its visible audience approval. Include `reply_count` when it is relevant to
  disagreement or discussion intensity.
- Do not dump large raw comment lists in either mode. If the available sample is small or partial, say so
  explicitly and do not present it as the whole audience view.
- Evidence attribution should be mode-aware. `quick` uses lightweight timestamps, inline screenshots,
  comment `like_count`, and evidence-file lists. `deep` should attribute key claims, disputed judgments,
  important data, and tutorial steps more explicitly.
- Do not cite every sentence, but important conclusions must be traceable to bundle evidence. Avoid
  paper-style footnote clutter unless the user explicitly asks for that style.
- Reports must distinguish source material from AI interpretation. Use lightweight labels such as
  `????`, `AI ??`, `????`, and `????` when useful, but do not label every sentence.
- AI-organized tables, charts, diagrams, risk notes, and evaluation should be presented as AI
  interpretation, not as source claims.
- `quick` should not add AI-made charts beyond the fixed multi-dimensional evaluation by default.
- `deep` may add AI-organized tables, diagrams, flowcharts, comparison charts, matrices, or timelines
  when they clarify the source. Label them as `AI ??` or `AI ??`, and keep their basis traceable
  to bundle evidence. Do not present them as original video screenshots or author-provided charts.
- Keep an evidence index at the end of both modes. `quick` lists key bundle files only; `deep` may list
  key screenshots, transcript/comparison files, cited comment files, and relevant diagnostics.
- Reports may include a lightweight `注意事项` module near the end. It should not dump raw tool logs; include
  only source cautions, diagnostics, and report limits that materially affect interpretation, such as
  transcript disagreement, missing or partial comments, missing visual evidence, OCR absence for
  screen-text-heavy videos, or platform permission/risk controls.
- Blocking diagnostic issues should stop substantive report writing and produce repair steps. Non-blocking
  diagnostic issues should be concise.

## Bundle Artifact Rules

- Standardized JSON/text files are the core evidence contract.
- `bundle.json` and `manifest.json` should point report skills toward normalized source artifacts.
- `manifest.json.command` records the latest manifest-writing operation; `manifest.json.command_history`
  preserves earlier operations so staged runs remain auditable.
- Raw provider files may be retained under `raw/` for debugging and audit.
- Raw files are not the primary report input, but retained working video/audio are required for staged transcription and frame extraction.
- Large raw HTML/API/video/audio dumps require an explicit option before implementation.
- Do not invent normalized files from missing provider data; record the missing artifact in diagnostics.

## Bundle Reuse Rules

- When the report workflow receives a video link or local video file, `video-bundle-prep` should create a new bundle by default.
- New bundles should use an output directory that distinguishes platform/source and run time, such as `outputs/<platform>-<source_id>-<timestamp>/`.
- If the user provides an existing bundle directory, read that bundle directly.
- For an existing bundle, `video-report` should run a light readiness/input check before writing the
  final report: read `bundle.json` and `diagnostics.json`, run `check-bundle`, and regenerate
  `report.input.json` only when it is missing or stale relative to core prepared artifacts such as
  `bundle.json`, `slides.json`, or `content_profile.json`.
- Existing bundle report runs must not redownload media, refetch comments, or rerun frame extraction
  unless the user explicitly asks to refresh source material.
- If the user explicitly asks to reuse the last result, the skill may read the latest matching bundle.
- Do not silently reuse old bundles for fresh link/file inputs, because metadata, transcript availability, comments, and diagnostics can change.

## Default Report Shape

- `docs/report-output-contract.md` is the canonical contract for quick/deep report structure, mode rules,
  image placement, AI evaluation, and audience-feedback handling. Keep this section consistent with it.
- `docs/report-visual-style.md` is the canonical contract for the accepted Template D / `Editorial Lab`
  visual baseline. Keep renderer work consistent with it unless the user explicitly reopens visual design.
- Report content structure v1 is frozen as of 2026-06-07. Do not change quick/deep content sections or
  report-mode boundaries unless the user explicitly reopens the content contract.
- `video-report` should start with a stable default report structure, but the final user-facing artifact must not stop at Markdown.
- Default final report artifacts are Chinese HTML plus long-image PNG exported from the same HTML.
- PDF is optional legacy/fallback output, not the preferred final report artifact.
- Long-image PNG should capture only the main report body and hide the left navigation while preserving the
  HTML layout.
- Markdown is acceptable only as an internal draft or fallback when HTML/PDF generation is blocked.
- Define quick/deep content structure before changing visual style or renderer layout. The HTML/PDF design
  should serve the agreed report sections, evidence density, and screenshot behavior.
- Reports support two formal modes:
  - `quick`: 快速总结. Use when the user wants to quickly understand what the video says, extract the
    main points, and decide whether the source deserves deeper study. Keep it concise, cover all source
    chapters or inferred sections inside the video overview, and use only a few key images when they
    materially improve understanding.
  - `deep`: 深入分析. Use when the user treats the video as learning/research material. Use richer
    image-text evidence, preserve chapters or create topic sections, and adapt the output toward either
    tutorial-style learning material or research/critical analysis based on the source type.
- Default report mode is `quick`.
- Do not auto-upgrade a report to `deep` merely because the video looks dense or tutorial-like.
- Use `deep` only when the user explicitly asks with a clear trigger such as `深入分析`, `深度报告`,
  `详细解读`, or `deep 模式`.
- If a `quick` report reveals that the video is suitable for deeper study, mention that `deep` mode is
  available instead of silently switching modes.
- `quick` and `deep` share the same final output formats and visual design system. The difference is
  content depth, analytical detail, and evidence density, not a separate HTML/PDF product.
- `quick` reports are not required to include images in every section. They may include a cover/thumbnail
  as the main visual in the video overview, and should embed timestamp screenshots directly inside the
  relevant overview or core-point discussion when the image supports that claim.
- Avoid a standalone "key image gallery" in `quick`; visuals should sit next to the point they explain.
- `quick` and `deep` should both include the same compact multi-dimensional rating graphic, such as a
  radar chart. This rating graphic should be the first content module after the top basic/source
  information, before the video overview, so the reader sees Codex's overall judgment immediately.
  The graphic is for quick visual orientation and does not need per-dimension reasons beside the chart;
  explain the reasoning later in the AI critique/detailed evaluation section.
- Default rating dimensions are credibility, originality, value density, argument strength, information
  density, and timeliness. Label the chart as AI evaluation, not source content.
- Use a 1-5 scale for each rating dimension. Do not use percentages or 0-10 scores by default; the rating
  is a compact judgment aid, not a precise measurement.
- `deep` reports should not have a fixed image-count ceiling in the product rules; report image volume
  should be chosen from source density, user goal, and readability.
- `deep` visuals should be embedded inside the relevant chapter/detail/core-viewpoint discussion. Do not
  create a standalone "key visual analysis" section unless the user explicitly asks for an image appendix.
- `deep` should not place a screenshot in every chapter or viewpoint by default. Include an image only when
  it adds information the text alone does not convey, and avoid repeated or near-identical screenshots.
- Talking-head, podcast, interview, and other low-visual-variation videos should not embed body screenshots
  by default. If a frame only repeats burned-in subtitles or shows the same speaker pose, keep screenshots as
  bundle evidence and use at most a representative hero frame; do not use them as report filler.
- Both `quick` and `deep` should avoid reusing the same screenshot in overview and later core/chapter
  sections. Keep a screenshot at the point where it most directly clarifies the text.
- For tutorial, course, software-demo, or process-heavy videos, `deep` should reconstruct the source into
  a readable text tutorial: concepts, steps, prerequisites, pitfalls, examples, and important screen states.
- For news, interview, speech, analysis, opinion, or market commentary videos, `deep` should focus on
  deeper content analysis: claims, assumptions, evidence, context, implications, disagreements, and risks.
- Do not add a standalone "适用人群" section by default. Applicability can appear as a small point inside
  the analysis when it is useful.
- Do not add generic "学习笔记" or "可执行清单" sections by default. Add checklists only when the source
  itself is procedural or the user explicitly asks for action items.
- `video-bundle-prep` should not reduce collection scope based on report mode. A prepared bundle is a
  reusable evidence library for the same source, so the user can run `quick` first and later run `deep`
  without collecting the source again.
- Report mode belongs to `video-report`, not to provider collection or bundle completeness. It may affect
  final report length, analysis depth, and how many prepared evidence items are rendered, but not the
  core bundle artifacts.
- `report.input.json` is also mode-independent. It should remain a reusable evidence index for the
  prepared bundle rather than a quick/deep-specific report input.
- Mode-specific final report content should use distinct filenames:
  - `report.content.quick.json`, `report.zh.quick.html`, `report.zh.quick.pdf`
  - `report.content.deep.json`, `report.zh.deep.html`, `report.zh.deep.pdf`
- When the user does not specify a mode, `quick` is the default. The renderer may also write compatibility
  aliases `report.content.json`, `report.zh.html`, and `report.zh.pdf` for the latest/default quick report.
- Reports must be image-text reports with selected screenshots/keyframes embedded inline and captioned.
- Report layout should be treated as product surface: include readable typography, section navigation, evidence cards, timeline/table sections, visual screenshots, audience feedback, and attention notes.
- `quick` default sections: basic information, AI multi-dimensional evaluation snapshot, video overview,
  core points with inline visual evidence when useful, AI critique, audience feedback, and
  attention notes/evidence.
- Basic information should include title, platform, author/uploader, publish time, duration, link, video
  type tags, view count when available, and like count when available.
- The quick video overview should concisely describe what the video covers and include the complete
  source chapter/section structure. Do not force it into a one-sentence conclusion.
- `deep` default sections: basic information, AI multi-dimensional evaluation snapshot, video overview
  and content map, original chapter/natural section detail, core viewpoint deep dive,
  audience feedback and disagreements, AI-organized visuals, AI detailed evaluation and critique,
  attention notes, and evidence index.
- Reports must cite local bundle files when making claims from extracted material.
- Reports must distinguish observed source material from AI inference.
- Missing artifacts should appear in `注意事项` instead of being silently ignored.
- Do not mention screenshot coverage in a normal report limitation section unless visual evidence is missing,
  failed, or materially incomplete.
- `report.input.json` is a compact evidence bridge for Codex. It may include selected screenshots, transcript
  windows, transcript-comparison flags, comment buckets, evidence files, and limitations for conversion into
  final-report attention notes.
- `report.content.draft.json` is a renderer scaffold only. It must not be treated as the final report content.
- `report.input.json` must be generated after semantic classification and frame extraction. It is not an input
  to the classification step and does not replace `content_profile.json`.
- `visual_selection_plan.json` is written by the prep agent after classification and transcript reading, then
  passed to `select-evidence --plan` and `prepare-report --plan`. It is the bridge between semantic intent
  and deterministic screenshot matching.
- `report.input.json` is an index into evidence. The final report workflow must still read the full transcript
  through `transcript.txt` or `transcript.segments.json` before writing mode-specific report content JSON.

## Minimum Evidence For Reports

- `video-report` must not write a substantive content report from metadata or comments alone.
- A substantive report requires transcript or audio transcription, plus screenshots, slides, or keyframes.
- If platform subtitles are unavailable, the provider should attempt local audio transcription from retained working audio before the skill gives up on the source.
- If platform subtitles are automatic rather than manual/official, the provider should retain the platform transcript as primary and create a whisper.cpp comparison transcript by default.
- When a comparison transcript exists, write `transcript.comparison.json` to highlight timestamped disagreements and technical-term differences without using an LLM.
- `--force-transcription` is a development smoke-test option only. Normal report runs must not force local transcription when platform subtitles are usable.
- `--no-compare-auto-subtitles` may disable the automatic-subtitle comparison path for faster diagnostics-only runs.
- Local whisper.cpp model choice must not be hard-coded by the skill. The engine should respect
  `VIDEO_BUNDLE_AGENT_WHISPER_MODEL` or `WHISPER_MODEL` first, then prefer installed turbo/large models before
  falling back to medium, small, and base models.
- FunASR is an optional experimental ASR backend for later Chinese-speed/quality comparison. It may be
  installed as the `funasr` extra, but it is not the default transcription path until smoke comparisons are
  documented.
- `video-bundle-prep` should run `video-bundle-agent check-bundle <bundle-dir>` as the evidence gate.
- `video-bundle-prep` should run `video-bundle-agent select-evidence <bundle-dir> --plan visual_selection_plan.json`
  before report writing when a plan exists.
- `video-bundle-prep` should run `video-bundle-agent prepare-report <bundle-dir> --plan visual_selection_plan.json`
  before `video-report`
  writes mode-specific final content.
- `prepare-report` must run after `content_profile.json` and `slides.json` exist.
- Missing comments may be marked as missing; this does not block the main content report.
- If a provider reports platform risk control for comments, such as Xiaohongshu `PERMISSION_REQUIRED`,
  the report should mention the audience-feedback limitation and continue when transcript/transcription
  and visual evidence are present.
- Missing transcript/transcription or missing screenshots/keyframes blocks the main content report unless the user explicitly asks for a diagnostic-only response.
- When core content evidence is missing, the skill should classify whether the source link/file is invalid or the local toolchain/provider failed.
- For toolchain/provider failures, the skill should explain the likely cause, give a concrete repair path, and retry after the issue is fixed before writing the report.
- The skill should not bypass the bundle engine to directly scrape webpages or APIs for missing core evidence.

## Visual Recall Rules

- Visual recall is core evidence for reports, not optional polish.
- Phase 1 should download a local video-only working file with a 1080p maximum target before extracting screenshots.
- If 1080p is unavailable, use the best available lower resolution and record the actual resolution.
- Keep the working video under `raw/media/` by default; add `--keep-media/--no-keep-media` later if needed.
- Do not use online stream seeking as the phase-1 default; it is more fragile because of signed URLs, headers, cookies, and seeking behavior.
- Phase 1 must implement `fixed_interval` screenshot extraction with `ffprobe` and `ffmpeg`.
- The bundle engine should support `--visual-recall none|low|medium|high`, defaulting to `medium`.
- `video-bundle-prep` should use `--visual-recall none` for stage-1 collection, classify the video, then run `extract-frames`.
- `low` means one screenshot every 15 seconds.
- `medium` means one screenshot every 5 seconds.
- `high` means one screenshot every 2 seconds.
- Candidate screenshot collection should prioritize complete visual coverage over small artifact counts.
- Default `max_screenshots` is `0`, meaning no candidate cap. A positive value is an explicit
  performance/storage limit for constrained runs.
- If interval extraction exceeds a positive `max_screenshots`, sample timestamps evenly across the video
  and record `VISUAL_COVERAGE_TRUNCATED` in diagnostics.
- Record candidate caps, unlimited mode, coverage completeness, sampling, and skipped candidate counts in
  `slides.json.extraction`.
- Screenshot candidates belong under `screenshots/candidates/`; later selected screenshots belong under `screenshots/selected/`.
- `slides.json` is the normalized visual index and should be listed through `bundle.json.slides_path`.
- The bundle engine may generate many screenshot candidates; `video-report` should not read every image by default.
- `video-report` should use transcript structure, chapters, timestamps, comments, and user focus as pointers to inspect important screenshots.
- If `source_chapters.json` exists, `video-report` must prefer those native source chapters over inferred
  sections. Bilibili `metadata.pages` is only page/part metadata and must not be mistaken for native chapters.
- YouTube should normalize yt-dlp `chapters` to `source_chapters.json` when present. Xiaohongshu currently has
  no reliable native chapter source; use natural sections unless source text itself contains timestamped
  structure.
- `select-evidence` should provide a small screenshot set and nearby transcript windows for normal report writing.
- `select-evidence` should prefer agent-authored semantic anchors from `visual_selection_plan.json` before
  falling back to built-in keyword matching and uniform timeline coverage.
- The agent decides what to look for: dynamic terms, time hints, source-type rationale, and whether an anchor
  needs an image. The tool only matches those pointers against transcript segments and candidate slides.
- `prepare-report` should persist that selected evidence in `report.input.json` so the skill can write the
  final report without rereading every bundle artifact or every screenshot.
- Copying selected screenshots into `screenshots/selected/`, visual duplicate removal, sharpness scoring, and
  brightness scoring remain future improvements.
- OCR is optional in phase 1. Create module boundaries and diagnostics, but do not block report readiness on OCR.
- If tesseract, PaddleOCR, or another OCR provider is missing, record `OCR_TOOL_MISSING`.
- OCR becomes a second-phase enhancement, especially for high visual recall, software demos, slides, and financial chart videos.
- Scene-change and keyword-trigger extraction are available as strategy options; screenshot selection, deduplication, and image scoring remain future improvements.
