# Platform Support

The bundle engine collects evidence. Report writing is handled by the Codex `video-report` skill after the
bundle is ready.

## Common Staged Flow

1. `analyze`: collect metadata, transcript/subtitles or local transcription, comments when requested, working
   media, thumbnail, diagnostics, and timings. In skill-led runs, screenshots are usually deferred with
   `--visual-recall none`.
2. Agent classification: Codex reads text evidence, writes `content_profile.json`, and writes
   `visual_selection_plan.json`.
3. `extract-frames`: use the plan for coarse baseline frames plus semantic-anchor screenshots.
4. `check-bundle`: verify transcript/transcription and screenshot readiness.
5. `select-evidence`: choose report-facing images from candidates.
6. `prepare-report`: write mode-independent `report.input.json`.
7. `video-report`: write `report.content.quick.json` or `report.content.deep.json`, then render HTML and long
   PNG.

## YouTube

Primary provider: `yt-dlp`.

Capabilities:

- metadata
- platform thumbnail
- native chapters from yt-dlp `chapters`
- subtitles and automatic subtitles
- optional local transcription comparison for automatic subtitles
- bounded comments through `yt-dlp --write-comments`
- retained working media for screenshots and transcription fallback

Default comment policy:

- `--comments --max-comments 100`
- top comments when the provider exposes sorting
- comments are non-blocking; failures go to `diagnostics.json`

## Bilibili

Primary provider: `bilibili-api-python`; `yt-dlp` is fallback only.

Capabilities:

- BV/AV/CID/page metadata
- UP/author metadata
- stats and thumbnail
- native chapters from player `view_points`
- platform subtitles from player subtitle APIs when available
- API playurl media download, with yt-dlp fallback only when needed
- language-aware local transcription fallback
- top-liked bounded comments

Bilibili login/cookies may be required for higher-quality media or complete comment pagination. Use
`scripts/refresh-bilibili-cookies.ps1` and pass the exported cookie file with `--cookies`.

Danmaku is disabled by default in the current product route.

## Xiaohongshu

Primary provider: lightweight note metadata/media collection plus MediaCrawler-only comments.

Capabilities:

- short-link resolution
- note metadata from HTML initial state or MediaCrawler detail fallback
- video/image media download when accessible
- local thumbnail asset
- language-aware local transcription for video notes
- screenshots/keyframes from retained video media
- bounded top-level comments through MediaCrawler's official `xhs detail` jsonl workflow

MediaCrawler:

- Default portable checkout: `external/MediaCrawler`
- Override: `XHS_MEDIACRAWLER_PATH`
- First run may open a browser for QR/SMS login
- Later runs should reuse MediaCrawler's saved browser profile
- Provider timeout is bounded; repeated login/risk-control failures are diagnostics, not endless retries

## Local Video

Provider: local media workflow.

Capabilities:

- copy/import local video into the bundle
- ffprobe metadata
- local audio extraction
- language-aware transcription
- screenshots/keyframes
- `audience_feedback.json` marked unavailable

Local video has no platform comments, online engagement metrics, or native chapters unless the user provides
separate metadata later. It can still produce a valid report when transcription and screenshots are ready.

## Visual Strategy

Skill-led runs should classify before screenshot extraction:

- Low visual variation: low recall, selective screenshots.
- Medium density: medium recall, coarse baseline plus anchors.
- High density tutorials/news/software/charts: high recall, plan-guided anchors.

`visual_selection_plan.json` is the bridge between agent judgment and deterministic ffmpeg screenshots.
The tool does not infer semantic importance by itself.
