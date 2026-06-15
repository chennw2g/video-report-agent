# Video Report Agent Plugin

`Video Report Agent` wraps the `video-bundle-agent` Python CLI for Codex.

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
