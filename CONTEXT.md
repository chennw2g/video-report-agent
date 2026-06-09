# Video Bundle Agent

This context defines the project language for a local tool that turns video sources into Codex-readable evidence bundles.

## Language

**Video Bundle Agent**:
The overall project that turns a video link or local video into a final Codex-written report through an automated bundle workflow.
_Avoid_: summarize fork, manual-only extractor

**Bundle**:
A directory of normalized source artifacts, diagnostics, and a manifest that Codex can inspect as evidence.
_Avoid_: Summary, report, cache dump

**Bundle Engine**:
The local Python CLI/package that gathers source material and writes a standard bundle without calling an LLM or writing the final report.
_Avoid_: Report skill, AI summarizer, plugin UI

**Video Bundle Prep Skill**:
A Codex skill that prepares evidence before report writing: it accepts a video link, local video file, or existing bundle, chooses the provider workflow, creates or updates the bundle, classifies the video from stage-1 text evidence, chooses the visual policy, extracts frames, checks readiness, and writes `report.input.json`.
_Avoid_: Final report writer, style template, AI summary output

**Video Report Skill**:
A Codex skill that writes the final user-facing report from a prepared bundle or `report.input.json`. It may invoke the Video Bundle Prep Skill workflow automatically when the user gives it a raw video link or local video file, but report writing remains a separate responsibility from evidence preparation.
_Avoid_: Provider, crawler, bundle engine, evidence collector

**Video Bundle Plugin**:
The eventual Codex packaging surface for this project. It can bundle the Video Bundle Prep Skill, the Video Report Skill, shared documentation, helper scripts, and the local bundle engine entrypoints so the user can trigger the whole workflow from Codex without manual shell orchestration.
_Avoid_: Single opaque AI summarizer, provider implementation, report-only template

**Stage-1 Bundle**:
A bundle created before screenshot extraction, containing metadata, transcript or transcription evidence, bounded audience feedback, diagnostics, and retained working media for later frame extraction.
_Avoid_: Final report bundle, text-only summary, completed visual bundle

**Content Profile**:
A Codex-authored bundle artifact that records the semantic video type, type tags, classification rationale, and chosen visual policy after stage-1 text evidence is available.
_Avoid_: Provider rule output, keyword-count classifier, metadata category

**Transcript Comparison**:
A deterministic, non-LLM bundle artifact that compares a primary transcript with an alternative transcript in timestamped windows and highlights likely disagreement points for Codex review.
_Avoid_: Final transcript correction, LLM transcript judge, automatic truth source

**Visual Policy**:
The Codex-selected frame extraction plan for a bundle, including visual recall level, extraction strategy, candidate screenshot cap, and rationale. A candidate cap of `0` means complete candidate coverage; report image count is controlled separately by evidence selection.
_Avoid_: Provider default, report style, fixed rule table, report image limit

**Provider**:
A platform adapter that knows how to collect source material from one source family, such as YouTube, Bilibili, Xiaohongshu, or local video.
_Avoid_: Plugin, scraper framework, report writer

**Phase 1**:
The first delivery slice whose success criterion is a stable, diagnosable bundle pipeline, not full feature coverage for every platform.
_Avoid_: MVP report generator, full crawler, all-platform parity

**Local Credentials**:
User-controlled cookies or authentication files stored outside the repository and passed explicitly to a provider run.
_Avoid_: Committed secrets, hidden default login state, bundled account data

**Xiaohongshu Signing Service**:
A bundled local signer, or an explicitly configured remote signer, used only as an explicit fallback/debug path for Xiaohongshu signed APIs. A remote signer may be passed through `--xhs-sign-url` or `XHS_SIGN_URL`. Signing does not replace cookies, account validity, or platform-side verification.
_Avoid_: Hidden browser scraping, account-risk bypass, treating signer success as valid platform permission

**MediaCrawler Comment Path**:
The default bounded Xiaohongshu comment recovery path that uses a separately checked-out MediaCrawler environment and an existing CDP Chrome session.
_Avoid_: Vendored crawler framework, long login loop, bulk crawling, complete-top100 claims from partial samples

**Platform Risk Diagnostic**:
A provider warning that a platform required additional verification, rejected the current account/session, or otherwise blocked optional audience feedback. For Xiaohongshu, observed `300011` comment failures are `PERMISSION_REQUIRED`; observed `-100` failures are `COOKIE_REQUIRED`.
_Avoid_: Silent retry loop, fake comment data, treating optional comments as a report blocker

**Audience Feedback**:
Bounded comments, danmaku, and lightweight engagement signals collected as evidence for a later report.
_Avoid_: Full comment archive, sentiment model output, social listening database

**Source Artifact**:
A normalized bundle file intended for Codex or a report skill to read directly as evidence.
_Avoid_: Raw provider dump, temporary download, debug file

**Raw Provider Data**:
Provider-native files retained only for debugging, audit, or parser improvement.
_Avoid_: Bundle contract, report input, normalized artifact

**Working Video**:
A retained local video file, preferably 1080p-or-best-available, used for transcription support and repeatable screenshot extraction.
_Avoid_: Archived full media library, provider source URL, final visual evidence

**Minimum Content Evidence**:
The minimum source material required before `video-report` may write a substantive report: transcript or audio transcription, plus visual screenshots or keyframes.
_Avoid_: Metadata-only report, comments-only report, impressionistic summary

**Visual Recall**:
The bundle capability that lets Codex inspect video画面 through screenshots, keyframes, OCR text, and related visual metadata.
_Avoid_: Decorative screenshots, thumbnail-only evidence, optional polish

**Screenshot Candidate**:
A frame image extracted from the video as potential visual evidence for Codex or the report skill.
_Avoid_: Final slide, thumbnail, raw video

**Frame Extraction Pass**:
A bundle update step that reads the working video and visual policy, extracts screenshot candidates, refreshes `slides.json`, and removes stale candidate screenshots from earlier extraction passes.
_Avoid_: Video classification, final evidence selection, report rendering

**Report Image Selection**:
The later bundle step that chooses a small number of screenshots and nearby transcript windows for `report.input.json`.
_Avoid_: Candidate screenshot cap, full visual coverage, final report writing
