# Release Checklist

Use this before publishing a public GitHub release.

## Repository Hygiene

- No cookies, API keys, login profiles, raw downloads, report outputs, or bundle outputs are committed.
- `external/` remains ignored; MediaCrawler is installed by bootstrap, not vendored.
- `archives/` remains local historical reference and is not part of the release.
- `.env.example` contains placeholders only.
- `docs/current-status.md` reflects the current capabilities and known gaps.

## Validation

Run from a clean checkout:

Windows:

```powershell
uv sync
uv run video-bundle-agent doctor
uv run pytest
uv run ruff check
uv build
uv run python C:\Users\chenn\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\video-report-agent
```

macOS:

```bash
bash scripts/bootstrap-macos.sh --install-tools --with-playwright --with-whisper-cpp --skip-doctor
uv run video-bundle-agent doctor
uv run pytest
uv run ruff check
uv build
```

For public CI, replace the local plugin validation path with the validator vendored by the target Codex
environment or document manual validation.

## Smoke Tests

- YouTube public video: metadata, transcript/subtitles or transcription, comments or diagnostics,
  screenshots, `report.input.json`.
- Bilibili video with cookies: metadata, native chapters/subtitles when available, comments, screenshots.
- Xiaohongshu video with MediaCrawler login profile: metadata/media, transcription, screenshots, comments or
  clear diagnostics.
- Local video file: ffprobe metadata, transcription, screenshots, report readiness.
- At least one `quick` and one `deep` report render to HTML and long PNG.

## Distribution Notes

- The release plugin is `plugins/video-report-agent`.
- The local workstation plugin is `plugins/video-report-agent-local` and should not be the public install
  target.
- Windows install scripts are PowerShell. macOS install scripts are Bash and assume Homebrew.
- The Python package name remains `video-bundle-agent`; the Codex plugin display name is
  `Video Report Agent`.
- The plugin requires a cloned repository workspace; it does not contain a standalone Python runtime.

## Known Non-Automated Items

- whisper.cpp CPU binary/model installation is automated on Windows through `scripts/install-whisper-cpp.ps1`
  and `scripts/bootstrap.ps1 -WithWhisperCpp`. macOS runtime/model installation is automated through
  `scripts/install-whisper-cpp-macos.sh` and `scripts/bootstrap-macos.sh --with-whisper-cpp`.
  CUDA prebuilt installs still depend on the target machine having a compatible NVIDIA runtime.
- Platform login and cookies remain user-controlled.
- Xiaohongshu comments depend on MediaCrawler and platform account state.
- OCR is optional and not part of the current required readiness gate.
