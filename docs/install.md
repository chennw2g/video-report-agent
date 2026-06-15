# Install

This project has checked install scripts for Windows and macOS. Linux may work for the Python CLI, but the
full plugin/report workflow is not packaged or validated for Linux yet.

## Quick Start

Clone the repository and run the bootstrap script from the project root.

Windows:

```powershell
git clone <repo-url> video-report-agent
cd video-report-agent

.\scripts\bootstrap.ps1 -InstallUv -WithPlaywright -WithWhisperCpp -InstallPlugin
```

macOS:

```bash
git clone <repo-url> video-report-agent
cd video-report-agent

bash scripts/bootstrap-macos.sh --install-tools --with-playwright --with-whisper-cpp --install-plugin
```

Then verify the local runtime:

```powershell
uv run video-bundle-agent doctor
uv run pytest
uv run ruff check
```

The bootstrap scripts intentionally separate safe project setup from optional system changes.

Windows `bootstrap.ps1`:

- Default: sync the Python project with `uv`.
- `-InstallUv`: install `uv` with the official Astral installer if it is missing.
- `-InstallWindowsTools`: use `winget` to install missing Python 3.12, Git, Node.js, and FFmpeg.
- `-WithPlaywright`: install the Playwright Chromium browser.
- `-WithWhisperCpp`: install a whisper.cpp Windows x64 runtime plus model files.
- `-WithFunASR`: install the optional Chinese ASR stack.
- `-WithMediaCrawler`: clone and sync MediaCrawler under `external/MediaCrawler`.
- `-InstallPlugin`: copy `plugins/video-report-agent` into the user's Codex personal plugin directory.

macOS `bootstrap-macos.sh`:

- Default: sync the Python project with `uv`.
- `--install-homebrew`: install Homebrew if missing.
- `--install-tools`: install Python 3.12, uv, ffmpeg, node, git, and tesseract through Homebrew.
- `--with-playwright`: install the Playwright Chromium browser.
- `--with-whisper-cpp`: install Homebrew `whisper-cpp` plus model files.
- `--with-funasr`: install the optional FunASR Python extra.
- `--with-mediacrawler`: clone and sync MediaCrawler under `external/MediaCrawler`.
- `--install-plugin`: copy `plugins/video-report-agent` into the user's Codex personal plugin directory.

## Full Local Report Runtime

For the full workflow across YouTube, Bilibili, Xiaohongshu, and local videos, install:

- Python 3.12
- uv
- FFmpeg and ffprobe
- Git
- Node.js, used by cookie export helpers and some yt-dlp JavaScript signature paths
- Chrome or Edge for cookie export and login-backed providers
- Optional: FunASR for Chinese local transcription
- Optional: whisper.cpp and a model file for English/other-language local transcription
- Optional: MediaCrawler for Xiaohongshu comments
- Optional: Tesseract for future OCR work

Recommended Windows bootstrap:

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

If you already manage external tools yourself, skip `-InstallWindowsTools` and set environment variables in
`docs/configuration.md`.

Recommended macOS bootstrap:

```bash
bash scripts/bootstrap-macos.sh \
  --install-tools \
  --with-playwright \
  --with-whisper-cpp \
  --with-funasr \
  --with-mediacrawler \
  --install-plugin
```

If you already manage external tools yourself, skip `--install-tools` and set environment variables in
`docs/configuration.md`.

## whisper.cpp

Install whisper.cpp runtime and the default models:

Windows:

```powershell
.\scripts\install-whisper-cpp.ps1
```

macOS:

```bash
bash scripts/install-whisper-cpp-macos.sh
```

Equivalent bootstrap forms:

```powershell
.\scripts\bootstrap.ps1 -WithWhisperCpp
```

```bash
bash scripts/bootstrap-macos.sh --with-whisper-cpp
```

Defaults:

- Windows runtime: official `ggml-org/whisper.cpp` `v1.8.6` Windows x64 CPU release.
- macOS runtime: Homebrew `whisper-cpp`.
- Main model: `ggml-large-v3-turbo.bin`.
- Language-probe model: `ggml-base.bin`.
- Windows install root: `VIDEO_BUNDLE_AGENT_TOOL_ROOT`, then `VIDEO_REPORT_AGENT_TOOL_ROOT`, then `D:\Workshop`.
- macOS install root: `VIDEO_BUNDLE_AGENT_TOOL_ROOT`, then `VIDEO_REPORT_AGENT_TOOL_ROOT`, then
  `~/.local/share/video-report-agent-tools`.

CUDA prebuilt packages are available when the target machine has a compatible NVIDIA runtime:

```powershell
.\scripts\install-whisper-cpp.ps1 -Backend cuda124
```

Use `-SetUserEnv` only if you want the script to write user-level model path variables. Otherwise the bundle
engine discovers models from the install root or normal environment variables.

On macOS, use `--set-shell-env` only if you want the script to append model path exports to `~/.zshrc`.

## Codex Plugin

The portable release plugin lives at:

```text
plugins/video-report-agent/
```

Install it locally:

Windows:

```powershell
.\scripts\install-plugin.ps1
```

macOS:

```bash
bash scripts/install-plugin-macos.sh
```

Then open Codex, install or refresh `Video Report Agent` from the personal plugin marketplace, and start a
new thread with this repository as the workspace.

The plugin is only a Codex workflow wrapper. The Python CLI, renderer, tests, and provider code still run
from the cloned repository root.

## Smoke Commands

```powershell
uv run video-bundle-agent doctor

uv run video-bundle-agent analyze "https://www.youtube.com/watch?v=474wZZHoWN4" `
  --out outputs/youtube-smoke `
  --comments `
  --max-comments 100 `
  --visual-recall none `
  --no-llm
```

For a full report, use the `video-report` skill or follow the staged prep workflow in
`docs/platform-support.md`.
