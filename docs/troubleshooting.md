# Troubleshooting

Start with:

```powershell
uv run video-bundle-agent doctor
```

Then inspect the bundle diagnostics:

```powershell
Get-Content outputs\<bundle>\diagnostics.json
Get-Content outputs\<bundle>\timings.json
```

## Required Tool Missing

Required tools are Python, uv, ffmpeg, ffprobe, and yt-dlp. If `doctor` reports one missing:

- On Windows, install it with `scripts/bootstrap.ps1 -InstallWindowsTools -InstallUv`, or
- On macOS, install it with `bash scripts/bootstrap-macos.sh --install-tools`, or
- Put the tool on `PATH`, or
- Set `VIDEO_BUNDLE_AGENT_TOOL_ROOT` to the directory tree that contains the tool.

## Transcript Missing

Reports require transcript or local audio transcription. Common causes:

- Platform subtitles unavailable and no working audio was downloaded.
- ffmpeg failed to extract audio.
- whisper.cpp or FunASR is missing when local transcription is needed.
- The source link requires login or has expired.

Do not write a substantive report from metadata/comments alone. Fix the blocker or mark the source invalid.

## whisper.cpp Missing

Install the default whisper.cpp runtime and models.

Windows:

```powershell
.\scripts\install-whisper-cpp.ps1
uv run video-bundle-agent doctor
```

macOS:

```bash
bash scripts/install-whisper-cpp-macos.sh
uv run video-bundle-agent doctor
```

If a CUDA backend fails to start because the target machine lacks a compatible NVIDIA runtime, install the
CPU backend instead:

```powershell
.\scripts\install-whisper-cpp.ps1 -Backend cpu
```

## Screenshot Missing

Reports require screenshots/keyframes. Common causes:

- The provider could not retain a working video file.
- ffprobe or ffmpeg failed.
- The source provides audio-only media.
- Platform login is required for a playable media URL.

Inspect `raw/media/`, `slides.json`, and `diagnostics.json`.

## YouTube Login or Signature Failure

Use explicit exported cookies when yt-dlp asks for sign-in:

Windows:

```powershell
.\scripts\refresh-youtube-cookies.ps1
uv run video-bundle-agent analyze "<url>" --cookies "$env:APPDATA\video-bundle-agent\youtube.cookies.txt"
```

macOS:

```bash
bash scripts/refresh-cookies-macos.sh --platform youtube
uv run video-bundle-agent analyze "<url>" \
  --cookies "$HOME/Library/Application Support/video-bundle-agent/youtube.cookies.txt"
```

If yt-dlp reports JavaScript signature issues, make sure the project dependency `yt-dlp[default]` is
installed with `uv sync` and Node is available when yt-dlp asks for it.

## Bilibili Quality or Comment Gaps

Use Bilibili cookies for high-quality media and more complete top-liked comment collection:

Windows:

```powershell
.\scripts\refresh-bilibili-cookies.ps1
uv run video-bundle-agent analyze "<url>" --cookies "$env:APPDATA\video-bundle-agent\bilibili.cookies.txt"
```

macOS:

```bash
bash scripts/refresh-cookies-macos.sh --platform bilibili
uv run video-bundle-agent analyze "<url>" \
  --cookies "$HOME/Library/Application Support/video-bundle-agent/bilibili.cookies.txt"
```

The provider should use Bilibili API first. If it falls back to yt-dlp, check the diagnostics and short-link
resolution result.

## Xiaohongshu Comments

Xiaohongshu comments require MediaCrawler in the current route:

```powershell
.\scripts\bootstrap.ps1 -WithMediaCrawler
```

```bash
bash scripts/bootstrap-macos.sh --with-mediacrawler
```

If MediaCrawler opens a browser, complete the platform login/verification. The saved profile should be
reused later. If comments still fail, keep the main bundle moving and treat comments as limited or missing.

## Encoding Damage

Final Chinese report content must be written with UTF-8. Do not generate Chinese JSON through PowerShell
pipes, here-strings, or `Set-Content`. Use `apply_patch` or a Python writer that opens files with
`encoding="utf-8"`.

The renderer refuses suspected mojibake by default. Fix the content file instead of disabling the guard.

## Slow Runs

Use `timings.json` to identify slow stages. Common slow points:

- local transcription on long videos
- MediaCrawler login/verification waits
- large screenshot candidate extraction
- report image rendering

The intended optimized flow is text first, then agent-authored visual selection, then targeted screenshots.
