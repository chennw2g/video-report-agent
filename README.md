# video-bundle-agent

`video-bundle-agent` is a lightweight Python tool for turning video sources into a Codex-readable bundle.

It does not summarize videos. Its job is only to collect, normalize, and package source material:

- metadata
- transcript, subtitles, or local audio transcription
- comments and audience feedback
- optional danmaku when explicitly requested
- screenshots or slide frames
- provider diagnostics
- a manifest that tells Codex what was collected and what failed

The previous `steipete/summarize` fork has already been archived under:

```text
archives/summarize-reference-20260606-020158/
```

## Current Scope

The first version should produce a stable local bundle from a video URL:

```text
video URL -> provider fetch -> normalized assets -> bundle directory
```

The bundle should be useful for later Codex analysis, report writing, or manual review.

## Non-goals

- No LLM summary generation in the core pipeline.
- No fake provider success.
- No committed cookies, API keys, or login state.
- No archival all-formats video download by default; YouTube keeps a 1080p-or-best-available working video for
  transcription and screenshots.
- No default full comment crawl.
- No dependency on the full `steipete/summarize` runtime as the product base.

## Initial Layout

```text
docs/project-plan.md        Project plan and phase boundaries
docs/provider-research.md   Final provider choices for phase 1
docs/bundle-schema.md       Bundle file schema and capability rules
docs/report-output-contract.md
                             Canonical quick/deep report content contract
src/video_bundle_agent/     Python package and CLI
tests/                      pytest tests
skills/video-bundle-prep/   Codex skill for preparing reusable bundle evidence
skills/video-report/        Codex skill for writing final quick/deep reports
plugins/video-report-agent-local/
                             Local Codex plugin wrapper for this workstation
plugins/video-report-agent/
                             Portable Codex plugin wrapper for GitHub/release installs
archives/                   Local reference archives, ignored by git
```

## Release Install

For a fresh clone, start here:

Windows:

```powershell
.\scripts\bootstrap.ps1 -InstallUv -WithPlaywright -WithWhisperCpp -InstallPlugin
uv run video-bundle-agent doctor
```

macOS:

```bash
bash scripts/bootstrap-macos.sh --install-tools --with-playwright --with-whisper-cpp --install-plugin
uv run video-bundle-agent doctor
```

For fuller local platform support, add optional switches:

Windows:

```powershell
.\scripts\bootstrap.ps1 `
  -InstallUv `
  -InstallWindowsTools `
  -WithPlaywright `
  -WithWhisperCpp `
  -WithFunASR `
  -WithMediaCrawler `
  -InstallPlugin
```

macOS:

```bash
bash scripts/bootstrap-macos.sh \
  --install-tools \
  --with-playwright \
  --with-whisper-cpp \
  --with-funasr \
  --with-mediacrawler \
  --install-plugin
```

The portable Codex plugin is:

```text
plugins/video-report-agent/
```

The plugin display name is `Video Report Agent`. It is a workflow wrapper; open the cloned repository as the
Codex workspace and run the Python CLI from the project root.

Release docs:

- `docs/install.md`
- `docs/configuration.md`
- `docs/platform-support.md`
- `docs/troubleshooting.md`
- `docs/release-checklist.md`
- `docs/github-publish.md`

## License

This project is licensed under GPL-3.0-or-later. The current provider stack includes
`bilibili-api-python`, which is GPL-3.0-or-later, so the repository uses a compatible copyleft license for
the first public alpha.

## Local Codex Plugin

The current local plugin wrapper lives in:

```text
plugins/video-report-agent-local/
```

Install or refresh it into the personal Codex plugin directory:

```powershell
.\scripts\install-local-plugin.ps1
```

This copies the plugin to:

```text
C:\Users\chenn\plugins\video-report-agent-local
```

and updates:

```text
C:\Users\chenn\.agents\plugins\marketplace.json
```

The local plugin is workstation-specific and kept as the tested wrapper for this machine. For public
release or another user's clone, use `plugins/video-report-agent/` and `scripts/install-plugin.ps1`.

## Development

The project uses Python, uv, Typer, Pydantic, pytest, and ruff.

```powershell
uv sync
uv run video-bundle-agent doctor
uv run pytest
uv run ruff check
```

First YouTube smoke path:

```powershell
uv run video-bundle-agent analyze "https://www.youtube.com/watch?v=474wZZHoWN4" `
  --out outputs/youtube-smoke `
  --comments `
  --max-comments 100 `
  --visual-recall medium `
  --visual-strategy auto `
  --no-llm

uv run video-bundle-agent check-bundle outputs/youtube-smoke
uv run video-bundle-agent select-evidence outputs/youtube-smoke --max-images 12
uv run video-bundle-agent prepare-report outputs/youtube-smoke --max-images 12
```

Bilibili smoke path uses the Bilibili API workflow first. `yt-dlp` is only a fallback when API metadata
or API media download fails. Anonymous Bilibili requests can be limited to low-resolution media and
small first-page comment samples; pass an explicit Bilibili Netscape cookies file with `--cookies`
when 1080p-or-better media and top 100 comment pagination are required:

```powershell
.\scripts\refresh-bilibili-cookies.ps1

uv run video-bundle-agent analyze "https://www.bilibili.com/video/BV1nU7X6wErT" `
  --out outputs/bilibili-smoke `
  --comments `
  --max-comments 100 `
  --visual-recall low `
  --visual-strategy fixed `
  --cookies "$env:APPDATA\video-bundle-agent\bilibili.cookies.txt" `
  --no-llm

uv run video-bundle-agent prepare-report outputs/bilibili-smoke --max-images 8
```

If Chrome's default profile cannot expose a DevTools endpoint, use the logged-in Edge profile:

```powershell
.\scripts\refresh-bilibili-cookies.ps1 `
  -ChromePath "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  -UseDefaultChromeProfile
```

Xiaohongshu basic provider uses explicit cookies when supplied, HTML note extraction, media download,
local transcription for video notes, and visual recall. Comments are collected through the managed
MediaCrawler checkout using its official detail/jsonl workflow. The portable default is
`external/MediaCrawler` under the cloned repository; override it with `XHS_MEDIACRAWLER_PATH`.
`XHS-Downloader` remains an external reference/tool and is not imported into the main package.

```powershell
.\scripts\refresh-xiaohongshu-cookies.ps1

uv run video-bundle-agent analyze "https://www.xiaohongshu.com/explore/<note-id>" `
  --out outputs/xiaohongshu-smoke `
  --comments `
  --max-comments 100 `
  --visual-recall high `
  --visual-strategy all `
  --no-llm
```

Xiaohongshu metadata and media can often be collected from the note HTML. Comment collection is
MediaCrawler-only: the first run may require QR/SMS verification in the browser that MediaCrawler opens,
then MediaCrawler reuses its saved `browser_data/cdp_xhs_user_data_dir` login state. If the login state
expires or Xiaohongshu triggers platform verification, the provider writes `COOKIE_REQUIRED` or
`PERMISSION_REQUIRED` diagnostics and continues with metadata/media/transcription.
Add `--cookies "$env:APPDATA\video-bundle-agent\xiaohongshu.cookies.txt"` only when the note HTML/media
request needs an exported Xiaohongshu cookie file.

Skill-led report runs can split text collection from screenshot extraction so Codex can classify the video first:

```powershell
uv run video-bundle-agent analyze "https://www.youtube.com/watch?v=474wZZHoWN4" `
  --out outputs/youtube-smoke `
  --comments `
  --max-comments 100 `
  --visual-recall none `
  --no-llm

# Codex reads metadata/transcript, writes content_profile.json, then runs:
uv run video-bundle-agent extract-frames outputs/youtube-smoke `
  --visual-recall high `
  --visual-strategy all `
  --max-candidate-screenshots 0

uv run video-bundle-agent check-bundle outputs/youtube-smoke
uv run video-bundle-agent prepare-report outputs/youtube-smoke --max-images 12
```

Screenshot candidate coverage and report image selection are separate. `--max-screenshots 0`
or `--max-candidate-screenshots 0` means no candidate cap, which is the default so dense tutorials,
software demos, chart videos, and news clips keep broad visual coverage. `prepare-report --max-images`
still controls how many images are placed into the compact report input.

`prepare-report` writes `report.input.json`, a compact mode-independent evidence bridge for the skill. It also writes
`report.content.draft.json` when the bundle is report-ready. The draft is renderer-compatible, but it is
not the final analysis; Codex should read `report.input.json`, inspect the selected screenshots and flagged
subtitle-comparison windows, then write mode-specific final report content such as
`report.content.quick.json` or `report.content.deep.json`.
The command prints a short status summary by default; use `--full-output` only when you need the full JSON
payload on stdout.

`prepare-report` is used after Codex has classified the video, written `content_profile.json`, and extracted
screenshots. It is an evidence index, not a replacement for the full transcript. Before writing the final
report, the skill should still read `transcript.txt` or `transcript.segments.json`.

The report skill renders the final Chinese image-text report with the bundled renderer. `quick` is the
default mode; use `deep` only when the user explicitly asks for `深入分析`, `深度报告`, `详细解读`,
or `deep 模式`.

The report content contract is documented in `docs/report-output-contract.md`. Its v1 content structure is
frozen as of 2026-06-07; the next report-output phase is visual style and renderer implementation.
The accepted visual baseline is Template D / `Editorial Lab`, documented in `docs/report-visual-style.md`:
light blue-green, left-navigation, evidence-first Chinese research brief. The static proof is
`outputs/report-style-variants/deep-template-d-editorial-lab-score-first.html`.

Audience feedback is mode-aware. `quick` summarizes a few main feedback directions and marks missing
comments briefly. `deep` may cite representative comment viewpoints with short original quotes, but cited
comments should include `like_count` when available so the reader can see visible audience approval.
Partial comment samples must be labelled as partial.

Evidence attribution is also mode-aware. `quick` keeps attribution light with timestamps, inline screenshots,
comment like counts, and evidence-file lists. `deep` attributes key claims, disputed judgments, important
data, and tutorial steps more explicitly without citing every sentence.

Both modes keep a final evidence index. `quick` lists key bundle files; `deep` may include used screenshots,
transcript/comparison files, cited comment files, and relevant diagnostics.

Reports may also include a lightweight diagnostic/trust note module for issues that materially affect
interpretation, such as transcript disagreement, partial comments, missing visual evidence, OCR absence for
screen-text-heavy videos, or platform permission/risk controls. In `quick`, keep it near limitations; in
`deep`, move it near the overview only when it changes core interpretation.

Reports should distinguish source material from AI interpretation. Use lightweight labels such as
`视频内容`, `AI 解读`, `观众反馈`, and `诊断提示` when useful, especially for AI-organized charts,
tables, risk notes, and evaluations.

AI-made visuals are limited by mode. `quick` only includes the fixed multi-dimensional evaluation chart
by default. `deep` may add AI-organized flowcharts, concept maps, comparison tables, matrices, or
timelines when they clarify the source; they must be labelled as AI-organized and traceable to evidence.
The compact AI multi-dimensional evaluation chart is rendered as the first content module after the top
basic/source information and before the video overview. Detailed rating reasoning stays later in the AI
critique/detailed evaluation section.

```powershell
python .\skills\video-report\scripts\render_report.py `
  --bundle-dir outputs\youtube-smoke `
  --content outputs\youtube-smoke\report.content.quick.json `
  --html outputs\youtube-smoke\report.zh.quick.html `
  --pdf outputs\youtube-smoke\report.zh.quick.pdf
```

Expected report artifacts:

```text
outputs/<bundle>/
|-- report.input.json
|-- report.content.draft.json
|-- report.content.quick.json
|-- report.zh.quick.html
|-- report.zh.quick.pdf
|-- report.content.deep.json
|-- report.zh.deep.html
`-- report.zh.deep.pdf
```

The tool writes partial bundles when a non-critical fetch fails. Missing transcripts, comments, danmaku,
slides, or OCR must be recorded in `diagnostics.json` rather than invented.

`video-report` requires both transcript/transcription and screenshots/keyframes before writing
a substantive report. YouTube stage-1 collection downloads a 1080p-or-best-available working video so screenshots
can be extracted later after Codex classifies the video; if subtitles are unavailable, it can also download working
audio, convert it with ffmpeg, and transcribe with the language-aware local engine: Chinese uses FunASR
Paraformer-zh + fsmn-vad + ct-punc + cam++, while English and other non-Chinese languages use whisper.cpp.
The engine does not rely only on platform metadata or title language: before full local transcription, it
cuts a short 16 kHz WAV probe and runs whisper.cpp language detection. The detected speech language routes
Chinese audio to FunASR and non-Chinese audio to whisper.cpp; platform/subtitle language hints are fallback
only when detection fails or returns low confidence.
`--visual-strategy auto` uses fixed-interval
frames for `low`, fixed plus keyword-trigger frames for `medium`, and fixed plus keyword plus scene-change frames
for `high`. Candidate screenshots are uncapped by default; use a positive `--max-screenshots` only when
time or disk space matters more than complete visual coverage.

For development smoke tests, `--force-transcription` can exercise the local transcription path even when yt-dlp
subtitles exist. It is disabled by default and should not be used for normal report runs.

Whisper model selection is local and configurable for English and other non-Chinese transcription. Set
`VIDEO_BUNDLE_AGENT_TOOL_ROOT` to point at an external tool tree and set `VIDEO_BUNDLE_AGENT_WHISPER_MODEL`
or `WHISPER_MODEL` to force a specific model file. On the original workstation, the active whisper.cpp CLI
is a CUDA build and `ggml-large-v3-turbo.bin` is the preferred English/other-language model. Whisper base
remains a CPU-only speed fallback candidate.

Language detection uses its own lightweight whisper.cpp model preference. Set
`VIDEO_BUNDLE_AGENT_WHISPER_LANGUAGE_MODEL` or `WHISPER_LANGUAGE_MODEL` to override it; otherwise the engine
prefers `ggml-base.bin` when available so the probe remains fast.

FunASR can be installed with the optional extra and is the default Chinese local-transcription backend:

```powershell
uv sync --extra funasr
```

The current default Chinese route is Paraformer-zh + fsmn-vad + ct-punc + cam++. Speaker labels, when
available, are anonymous voice-cluster ids rather than real names.

When yt-dlp only finds automatic subtitles, normal YouTube runs also create a language-aware local
transcription comparison transcript by default. Disable that extra work with `--no-compare-auto-subtitles`
when speed matters more than transcript cross-checking.

Automatic-subtitle comparison also writes `transcript.comparison.json`, a timestamped diff summary that highlights
technical-term disagreements such as `computer` vs `compute`.

If YouTube asks yt-dlp to sign in, pass authentication explicitly:

```powershell
.\scripts\refresh-youtube-cookies.ps1

uv run video-bundle-agent analyze "https://www.youtube.com/watch?v=474wZZHoWN4" `
  --out outputs/youtube-smoke `
  --comments `
  --max-comments 100 `
  --visual-recall medium `
  --cookies "$env:APPDATA\video-bundle-agent\youtube.cookies.txt" `
  --no-llm
```

Cookies are never read by default and must not be committed to the repository.
`--cookies-from-browser chrome` is available, but this Windows machine has already shown DPAPI
decryption failures with direct Chrome cookie reads, so the exported cookies file is the stable path.
The project depends on `yt-dlp[default]` so the Python yt-dlp path includes `yt-dlp-ejs`; current YouTube
downloads may also need `--js-runtimes node` when YouTube presents an EJS challenge.
