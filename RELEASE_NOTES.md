# video-report-agent 0.1.0-alpha.2

## 中文说明

`Video Report Agent` 是一个本地视频资料准备与中文图文报告生成工作流。它可以读取 YouTube、Bilibili、小红书链接或本地视频，采集元数据、章节、字幕/转录、截图、评论和诊断信息，生成可审计的本地证据包，并由 agent 输出 quick/deep 中文 HTML 与长图报告。

对外项目名称是 `Video Report Agent`。`video-bundle-agent` 只是内部 Python CLI 名称，负责证据包准备，不代表整个项目名称。

## English

First public-ready alpha for local video report workflows.

This supersedes `0.1.0-alpha.1` with final GitHub Actions cleanup and release-status documentation.

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
- GitHub Actions release tags pinned to current exact versions:
  `actions/checkout@v6.0.3`, `actions/setup-python@v6.2.0`, and `astral-sh/setup-uv@v8.2.0`.

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
