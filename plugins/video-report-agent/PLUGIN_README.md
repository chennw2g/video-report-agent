# Video Report Agent Plugin

`Video Report Agent` 是一个本地视频资料准备与中文图文报告生成插件。它读取视频链接或本地视频，准备字幕/转录、截图、评论、元数据和诊断证据，然后生成 quick/deep 中文 HTML 与长图报告。

`video-bundle-agent` 是插件内部调用的 Python CLI，负责证据包准备；对外插件名称是 `Video Report Agent`。

---

`Video Report Agent` wraps the internal `video-bundle-agent` Python CLI for Codex.

The plugin contains two skills:

- `video-bundle-prep`: collect and prepare reusable video evidence bundles.
- `video-report`: write Chinese quick/deep HTML and long-PNG reports from prepared evidence.

This release plugin is portable. It does not assume Chenn's local paths. Install the Python environment and
external tools from the repository root before using the plugin:

Windows:

```powershell
.\scripts\bootstrap.ps1 -InstallPlugin
uv run video-bundle-agent doctor
```

macOS:

```bash
bash scripts/bootstrap-macos.sh --install-plugin
uv run video-bundle-agent doctor
```

See:

- `docs/install.md`
- `docs/configuration.md`
- `docs/platform-support.md`
- `docs/troubleshooting.md`
