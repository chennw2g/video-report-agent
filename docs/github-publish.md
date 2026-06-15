# GitHub Publish Guide

This guide assumes the repository is ready locally and you want to publish it to GitHub.

## Local Release Gate

Run:

```bash
uv sync
uv run ruff check
uv run pytest
uv build
uv run video-bundle-agent doctor
```

On Windows, also parse PowerShell scripts:

```powershell
$files = @(
  'scripts/bootstrap.ps1',
  'scripts/install-plugin.ps1',
  'scripts/install-whisper-cpp.ps1',
  'scripts/refresh-youtube-cookies.ps1',
  'scripts/refresh-bilibili-cookies.ps1',
  'scripts/refresh-xiaohongshu-cookies.ps1'
)
foreach ($file in $files) {
  $null = [scriptblock]::Create((Get-Content -Raw $file))
}
```

On macOS, parse shell scripts:

```bash
bash -n scripts/bootstrap-macos.sh scripts/install-plugin-macos.sh \
  scripts/install-whisper-cpp-macos.sh scripts/refresh-cookies-macos.sh
```

## Push

If a GitHub repository already exists:

```bash
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
```

If using GitHub CLI:

```bash
gh repo create <owner>/<repo> --source . --private --push
```

Switch `--private` to `--public` when ready.

## First Release Tag

Do not tag `v0.1.0` until:

- CI passes on Windows and macOS.
- A clean clone can run the documented bootstrap path.
- At least one YouTube or local-video smoke produces a ready bundle and report.
- License and third-party notices are acceptable for the chosen distribution model.

After that:

```bash
git tag v0.1.0
git push origin v0.1.0
```
