# Contributing

This project is currently alpha software. Contributions should keep the core boundary intact:

- The Python CLI collects evidence bundles and does not call an LLM.
- Codex skills classify evidence and write final reports.
- Cookies, login state, raw media, and generated outputs must not be committed.

## Development Setup

Windows:

```powershell
.\scripts\bootstrap.ps1 -InstallUv -WithPlaywright -WithWhisperCpp
uv run video-bundle-agent doctor
```

macOS:

```bash
bash scripts/bootstrap-macos.sh --install-tools --with-playwright --with-whisper-cpp
uv run video-bundle-agent doctor
```

## Validation

Run before opening a pull request:

```bash
uv run ruff check
uv run pytest
uv build
```

When behavior changes, update `docs/current-status.md` and any relevant workflow docs.

## Provider Rules

- Do not bypass platform login, payment, DRM, CAPTCHA, or risk controls.
- Keep comments bounded by default.
- Record failures in `diagnostics.json`; do not fake missing evidence.
- Do not add bulk scraping behavior without a documented design decision.

## Report Rules

- Final reports require transcript or audio transcription plus screenshots/keyframes.
- Comments are optional and should be marked missing or partial when unavailable.
- Final Chinese report content must be written through UTF-8-safe paths.

