# Configuration

Runtime configuration uses environment variables. The repository includes `.env.example` as a reference, but
the Python app does not auto-load `.env`; set variables in your shell, PowerShell profile, CI job, or Codex
environment before running `uv run video-bundle-agent ...`.

## Tool Paths

`VIDEO_BUNDLE_AGENT_TOOL_ROOT`

External tool/model root.

- Windows default fallback: `D:/Workshop`
- macOS/Linux default fallback: `~/.local/share/video-report-agent-tools`

Portable installs should either put tools on `PATH` or set this variable.

`VIDEO_REPORT_AGENT_TOOL_ROOT`

Alias accepted for the same purpose.

`XHS_MEDIACRAWLER_PATH`

MediaCrawler checkout for Xiaohongshu comments. If unset, the project checks:

1. `external/MediaCrawler` under the cloned repository
2. `external/MediaCrawler` under the current working directory
3. `D:/W/Codex/external/MediaCrawler` as the original workstation fallback

## Whisper.cpp

Install the default whisper.cpp runtime and models:

Windows:

```powershell
.\scripts\install-whisper-cpp.ps1
```

macOS:

```bash
bash scripts/install-whisper-cpp-macos.sh
```

The scripts install or locate the runtime, then download model files into `whisper.cpp/models` under the
configured tool root.

`VIDEO_BUNDLE_AGENT_WHISPER_MODEL` or `WHISPER_MODEL`

Force the whisper.cpp model used for English and other non-Chinese local transcription.

`VIDEO_BUNDLE_AGENT_WHISPER_LANGUAGE_MODEL` or `WHISPER_LANGUAGE_MODEL`

Force the smaller whisper.cpp model used for the language probe before full local transcription.

The project prefers local audio language probing over title/platform language hints. Chinese audio routes to
FunASR when installed; non-Chinese audio routes to whisper.cpp.

## Cookies

Cookies are not read implicitly and must not be committed. Pass cookie files explicitly:

Windows:

```powershell
uv run video-bundle-agent analyze "<url>" `
  --cookies "$env:APPDATA\video-bundle-agent\youtube.cookies.txt" `
  --out outputs/example `
  --comments `
  --max-comments 100 `
  --no-llm
```

macOS:

```bash
uv run video-bundle-agent analyze "<url>" \
  --cookies "$HOME/Library/Application Support/video-bundle-agent/youtube.cookies.txt" \
  --out outputs/example \
  --comments \
  --max-comments 100 \
  --no-llm
```

Helper scripts:

Windows:

```powershell
.\scripts\refresh-youtube-cookies.ps1
.\scripts\refresh-bilibili-cookies.ps1
.\scripts\refresh-xiaohongshu-cookies.ps1
```

macOS:

```bash
bash scripts/refresh-cookies-macos.sh --platform youtube
bash scripts/refresh-cookies-macos.sh --platform bilibili
bash scripts/refresh-cookies-macos.sh --platform xiaohongshu
```

Default cookie locations:

```text
%APPDATA%\video-bundle-agent\youtube.cookies.txt
%APPDATA%\video-bundle-agent\bilibili.cookies.txt
%APPDATA%\video-bundle-agent\xiaohongshu.cookies.txt
$HOME/Library/Application Support/video-bundle-agent/youtube.cookies.txt
$HOME/Library/Application Support/video-bundle-agent/bilibili.cookies.txt
$HOME/Library/Application Support/video-bundle-agent/xiaohongshu.cookies.txt
```

## Codex Plugin Runtime

The plugin directory is not the runtime root. In Codex, open the cloned repository as the workspace and run
commands from the directory containing `pyproject.toml`.
