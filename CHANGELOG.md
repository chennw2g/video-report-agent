# Changelog

## 0.1.0-alpha.2 - 2026-06-15

Release cleanup after the first alpha publication:

- Pinned GitHub Actions to exact current release tags:
  `actions/checkout@v6.0.3`, `actions/setup-python@v6.2.0`, and `astral-sh/setup-uv@v8.2.0`.
- Confirmed CI passes on Windows and macOS after the action tag update.
- Updated release notes and status documentation to point at the current published alpha.

## 0.1.0-alpha.1 - 2026-06-15

Initial public-ready alpha packaging:

- Python `video-bundle-agent` CLI for video evidence bundles.
- Codex `Video Report Agent` release plugin with `video-bundle-prep` and `video-report` skills.
- YouTube, Bilibili, Xiaohongshu, and local-video provider workflows.
- Chinese quick/deep HTML and long-PNG report workflow.
- Windows and macOS bootstrap scripts.
- whisper.cpp installer scripts and model download support.
- MediaCrawler integration path for Xiaohongshu comments.
