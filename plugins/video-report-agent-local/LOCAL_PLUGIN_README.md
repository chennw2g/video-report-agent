# Video Report Agent Local Plugin

This is the local Codex plugin wrapper for the `video-bundle-agent` engine on Chenn's Windows workstation.
The user-facing plugin name is `Video Report Agent`, because the plugin's job is to turn video inputs into
final reports.

It is intentionally local-only for now. It does not install Python, uv, ffmpeg, whisper.cpp, FunASR,
MediaCrawler, cookies, or browser login state. It expects the existing project environment to remain in:

```text
D:\W\Codex\video-summarize-program
```

## Included Skills

- `video-bundle-prep`: prepares reusable evidence bundles from YouTube, Bilibili, Xiaohongshu, or local video.
- `video-report`: writes Chinese quick/deep HTML and long-PNG reports from prepared evidence.

## Local Runtime Assumptions

- Python project root: `D:\W\Codex\video-summarize-program`
- CLI entrypoint: `uv run video-bundle-agent`
- MediaCrawler checkout: `D:\W\Codex\external\MediaCrawler`
- whisper.cpp CUDA CLI: `D:\Workshop\whisper.cpp\v1.8.6-cuda\Release\whisper-cli.exe`
- Cookie files:
  - `%APPDATA%\video-bundle-agent\youtube.cookies.txt`
  - `%APPDATA%\video-bundle-agent\bilibili.cookies.txt`
  - `%APPDATA%\video-bundle-agent\xiaohongshu.cookies.txt`

## Local Smoke

Run from the project root:

```powershell
uv run video-bundle-agent doctor
uv run pytest
uv run ruff check
```

Install or refresh this local plugin from the project root:

```powershell
.\scripts\install-local-plugin.ps1
```

After reinstalling or refreshing the plugin, start a new Codex thread so the app loads the updated skills.
