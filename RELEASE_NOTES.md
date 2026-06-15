# video-report-agent 0.1.0-alpha.1

First public-ready alpha for local video report workflows.

## What Is Included

- Python `video-bundle-agent` CLI for collecting video evidence bundles.
- Codex `Video Report Agent` plugin with two skills:
  - `video-bundle-prep`
  - `video-report`
- YouTube, Bilibili, Xiaohongshu, and local-video preparation workflows.
- Chinese quick/deep HTML and long-PNG report workflow.
- Windows and macOS bootstrap scripts.
- whisper.cpp installer scripts and model download support.
- Xiaohongshu MediaCrawler integration path for bounded top-level comments.
- GitHub CI for Windows and macOS.

## Install

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

## Notes

- This is an alpha release.
- The project is GPL-3.0-or-later because the current Bilibili provider depends on
  `bilibili-api-python`.
- macOS scripts are best-effort from Windows development and should be validated on a real macOS host.
- Platform cookies, login state, raw media, generated bundles, and report outputs must not be committed.
