# Provider Research

This document records the phase-1 provider choices.

## Current Decision

Do not use the full `steipete/summarize` fork as the main application base.

Use it only as a reference archive for:

- YouTube smoke-test behavior
- yt-dlp cookie handling
- Windows dependency checks
- slide/frame extraction ideas
- Bilibili API-first provider boundaries and fallback behavior

## YouTube

Primary provider: `yt-dlp`.

Responsibilities:

- metadata
- native chapters when yt-dlp exposes `chapters`
- subtitles / automatic subtitles
- comments through `--write-comments`
- 1080p-or-best-available working video for screenshots
- working audio when subtitle/transcript fallback needs local transcription
- thumbnail
- basic format information

YouTube comments will not use the YouTube Data API in phase 1.
Default behavior must never fetch all comments.
Authentication is explicit only: use `--cookies PATH` or `--cookies-from-browser chrome` when yt-dlp
reports `COOKIE_REQUIRED`. On this Windows machine, direct browser cookie decryption can fail with
DPAPI errors, so the stable path is `scripts/refresh-youtube-cookies.ps1`, which writes a Netscape
cookies file under `%APPDATA%\video-bundle-agent\youtube.cookies.txt`.

Defaults:

```json
{
  "comment_sort": "top",
  "max_comments": 100
}
```

For `yt-dlp`, this maps to:

```text
--write-comments --extractor-args "youtube:comment_sort=top;max_comments=100"
```

YouTube feedback capabilities:

```json
{
  "has_danmaku": false,
  "has_comments": true,
  "has_audience_feedback": true
}
```

Transcript fallback:

- Try yt-dlp subtitles / automatic subtitles first.
- If no usable subtitle is available, download a bounded working audio file.
- Convert the audio to 16 kHz mono WAV with ffmpeg.
- Transcribe with local whisper.cpp when available.
- whisper.cpp model choice is local and configurable. `VIDEO_BUNDLE_AGENT_WHISPER_MODEL` or `WHISPER_MODEL`
  overrides all defaults; otherwise the engine prefers installed `large-v3-turbo` / turbo variants before
  falling back to large, medium, small, and base models.
- If the local transcription tool or model is missing, write diagnostics instead of inventing transcript text.
- Keep forced local transcription behind an explicit development option; do not enable it by default.
- If yt-dlp reports only automatic captions and no manual subtitles, keep the platform transcript as primary and
  write a whisper.cpp comparison transcript by default.
- Write `transcript.comparison.json` so downstream Codex can inspect timestamped disagreements instead of manually
  diffing full transcript files.
- FunASR is installed as an optional experimental backend. A 2026-06-12 same-audio benchmark compared
  Whisper large-v3-turbo, SenseVoiceSmall + fsmn-vad + cam++, and Paraformer-zh + fsmn-vad + ct-punc +
  cam++ on a Chinese Bilibili video and an English YouTube video. Keep normal provider routing on
  whisper.cpp for now; Paraformer-zh is the leading Chinese-speed candidate, while Whisper remains the
  English/default-quality choice.

YouTube chapter handling:

- If yt-dlp returns `chapters`, normalize them to `source_chapters.json` with
  `chapter_source = "yt_dlp.chapters"`.
- If yt-dlp does not return chapters, write an empty `source_chapters.json`; report writing should then infer
  natural sections from transcript/slides and should not pretend those inferred sections are official chapters.
- YouTube chapters are only as accurate as the platform/yt-dlp metadata. They may come from uploader-created
  chapters or platform-derived chapter metadata depending on the video.
- On current YouTube, Python `yt-dlp` may need the official EJS challenge components. Keep
  `yt-dlp[default]` in project dependencies and use `--js-runtimes node` when format extraction returns only
  storyboard images with an `n challenge solving failed` warning.

## Bilibili

Primary combination: `Nemo2011/bilibili-api` (`bilibili-api-python`) + `yt-dlp` fallback.

Current implementation stage: `bilibili-api-python` primary provider with bounded top-liked comments,
optional danmaku, API playurl media download, local transcription, and `yt-dlp` fallback only when
the API path cannot produce enough media/metadata.

`bilibili-api-python` responsibilities:

- BV / AV / CID / part detection
- metadata, stats, thumbnail, and UP information
- native player chapters through player `view_points` when available
- bounded top-liked comments
- optional danmaku only when explicitly requested
- playurl/DASH media URLs for local video/audio download
- provider raw files for audit under `raw/bilibili_api/`

API media download responsibilities:

- Select a 1080p-or-best-available video stream and best available audio stream.
- Download DASH video/audio with `httpx` and Bilibili referer headers.
- Mux video/audio with ffmpeg into a retained working video under `raw/media/`.
- Use retained audio for whisper.cpp transcription when subtitles are unavailable.
- Use retained working video for fixed/keyword/scene visual recall through the shared frame extractor.

`yt-dlp` fallback responsibilities:

- fallback metadata only if the API metadata path fails
- fallback working video/audio only if the API playurl/media path fails
- diagnostics for `COOKIE_REQUIRED`, `RATE_LIMITED`, or provider extraction failures

Current boundaries:

- Bilibili links should enter the Bilibili provider workflow directly; do not run a default
  YouTube/yt-dlp-first path just to discover that it fails.
- `bilibili-api-python` is the first source for BV/AV/CID/pages/stat/UP metadata.
- `metadata.pages` is page/part metadata only. Native progress-bar chapters should be fetched separately
  from player `view_points` and normalized to `source_chapters.json`.
- `bilibili-api-python` fetches bounded top-liked comments.
- `bilibili-api-python` playurl data is the first media source, avoiding known Bilibili HTTP 412
  noise from a default yt-dlp pass.
- `bilibili-api-python` playurl asks for high-quality DASH streams (`qn=127`, `fnval=4048`,
  `fourk=1`), but anonymous requests can still be restricted to low-resolution streams. Pass
  explicit Bilibili cookies when 1080p-or-better screenshots are required.
- `yt-dlp` is a fallback, not the success-path provider.
- If the API path fails, write `BILIBILI_API_UNAVAILABLE`, `COMMENTS_UNAVAILABLE`, or
  `DANMAKU_UNAVAILABLE` diagnostics instead of inventing data. If player chapters cannot be fetched, write
  `SOURCE_CHAPTERS_UNAVAILABLE` and let the report infer natural sections from transcript/slides.

Default Bilibili comment collection should be top 100 by `like_count` descending until the user explicitly
requests a different limit.
Anonymous Bilibili comment APIs may expose the total count but return only a small first-page sample;
authenticated pagination requires an explicit Bilibili Netscape cookies file passed with `--cookies`.
If fewer comments are fetched than requested, keep the partial `comments.json` and write a warning
diagnostic instead of implying top 100 was collected.
Danmaku is disabled by default (`--max-danmaku 0`) because current phase-1 reports do not need it and
Bilibili danmaku does not expose a reliable like-count ranking. If danmaku is explicitly enabled later,
it must remain bounded and record sampling details.

This is a personal local tool, so GPLv3 distribution concerns are not a phase-1 blocker.
Function coverage and implementation speed take priority.

## Xiaohongshu

Primary references: `XHS-Downloader` + `MediaCrawler` + `ReaJason/xhs`.

Current implementation stage: lightweight Xiaohongshu provider boundary with HTML initial-state note extraction,
media URL normalization, media file download, video transcription, visual recall, and MediaCrawler-only bounded
comment fetching. The old `xhs` plus bundled local signer path has been removed from the supported workflow.
`XHS-Downloader` is installed as an external reference/tool under
`D:\Workshop\XHS-Downloader`, but it is not imported into the main project because the current repo does not
build as a standard Python wheel and should not be vendored into the bundle engine. `MediaCrawler` is checked
out under `D:\W\Codex\external\MediaCrawler` with its own uv environment and is treated as a managed external
runtime for Xiaohongshu comments, similar to how the project wraps ffmpeg, yt-dlp, and whisper.

`XHS-Downloader` responsibilities:

- note details
- video/image download URLs
- note file download
- API/MCP call reference

`MediaCrawler` responsibilities:

- comments
- nested comments
- search
- author homepage
- audience feedback analysis

Default Xiaohongshu comment collection should be top 100 only. Nested comments must also be bounded before
implementation.

Current comment boundary:

- Top-level comments use MediaCrawler's official `xhs detail` workflow when
  `D:\W\Codex\external\MediaCrawler` exists, or when `XHS_MEDIACRAWLER_PATH` points to another checkout.
  The wrapper runs MediaCrawler in its own uv environment, sets CDP auto-launch with saved login state, writes
  raw `jsonl` files under `raw/xiaohongshu/mediacrawler/`, and caps/sorts normalized comments by `like_count`.
- The bundled local signer from `src/video_bundle_agent/providers/xiaohongshu/signer.py`, the `xhs-signer`
  command, `--xhs-sign-url`, and `XHS_SIGN_URL` are removed from the supported workflow because observed real
  comment calls were unstable.
- 2026-06-11 retest: after exporting fresh cookies from the logged-in dedicated CDP browser, the original
  `xhs` + builtin local signer path still returned `300011` (`当前账号存在异常，请切换账号后重试`) on
  `SRjpwmmZKw`. Do not promote it back unless a new ADR explicitly replaces the MediaCrawler-only decision.
- Signing and CDP browser state are not replacements for platform permission. If Xiaohongshu blocks the
  current account/session, record diagnostics and continue with core video evidence.
- If Xiaohongshu returns interactive verification or account/session risk responses such as `300011`,
  comments are recorded as `PERMISSION_REQUIRED` diagnostics and the bundle continues without comments.
- If Xiaohongshu returns login-expired responses such as `-100`, comments are recorded as `COOKIE_REQUIRED`.
- Normalized comments are sorted by `like_count` descending and capped by `--max-comments`, default 100.
- Nested comments remain deferred until a bounded policy and extraction flow are validated.
- MediaCrawler login is allowed only as its normal saved-profile flow. The first run may require QR/SMS
  verification; later runs should reuse `browser_data/cdp_xhs_user_data_dir`. Do not keep repeating QR/SMS
  login attempts once the provider has captured a platform error clearly.
- MediaCrawler detail runs are intentionally bounded by the provider timeout, currently 180 seconds. A longer
  wait usually means the opened browser is waiting for login, verification, or a platform gate, so the workflow
  should stop with diagnostics instead of silently waiting.
- Observed MediaCrawler smoke for `http://xhslink.com/o/AAljrp051vx`: CDP cookies were present, `selfinfo`
  returned `code=-104` / no permission, note detail API hit CAPTCHA `461`, but the comment endpoint returned
  three top-level comments. This proves the fallback can recover some comments, but it must not be labelled
  as complete top 100 when the platform only returns a small sample.

`ReaJason/xhs` responsibilities:

- lightweight note client reference
- field shape reference

Xiaohongshu chapter handling:

- The current Xiaohongshu provider does not have a reliable platform-native chapter source.
- Do not write invented `source_chapters.json` items for Xiaohongshu.
- For Xiaohongshu videos, reports should use Codex natural sections based on note text, transcript,
  screenshots, and media structure. If the note author writes timestamped sections in the description,
  those can be cited as source text, but they are not treated as a separate platform chapter API.

Current login boundary:

- Stable local cookie path: `%APPDATA%\video-bundle-agent\xiaohongshu.cookies.txt`.
- Refresh helper: `scripts/refresh-xiaohongshu-cookies.ps1`.
- MediaCrawler comment login state: `D:\W\Codex\external\MediaCrawler\browser_data\cdp_xhs_user_data_dir`
  by default, or the equivalent `browser_data` directory under `XHS_MEDIACRAWLER_PATH`.
- The old `scripts/start-xiaohongshu-cdp-chrome.ps1` / port `9231` path is no longer the normal workflow.
  It can remain as a manual debugging helper, but the provider should call MediaCrawler's official workflow
  and let MediaCrawler auto-launch/save its own browser profile.
- Cookies are passed explicitly with `--cookies`; direct `--cookies-from-browser` is not supported for
  Xiaohongshu.

External reference notes:

- `WJS-WEB/xiaohongshu-sentiment-analysis` is a Selenium/Chrome DOM scraping reference for comments and
  PDF sentiment reports. It may be useful for a future browser-state comment fallback that scrolls the
  logged-in web page and parses visible comment nodes.
- It does not appear to solve signed API comments or observed API risk-control responses such as `300011`.
  Do not import it as the primary provider path. If used, keep it behind a bounded, explicit browser-fallback
  adapter and record diagnostics when selectors, login, or platform verification fail.

Do not copy the full `MediaCrawler` source tree into `src/video_bundle_agent/`.
Keep it as a managed external checkout with a small adapter/provider boundary.

## Safety Notes

- Cookies may be needed for some providers, but must live outside the repository.
- API keys must never be committed.
- Provider failures should be represented in `diagnostics.json`.
- Do not bypass platform risk controls, captchas, paywalls, DRM, or account restrictions.
