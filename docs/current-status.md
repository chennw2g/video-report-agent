# Current Status

Last updated: 2026-06-15 22:48 +08:00

This file is the short project snapshot to read after context compaction. Update it after every material
project change that affects capabilities, provider state, report contracts, validation status, known blockers,
external tool state, or recommended next steps.

## Project State

- The repo is the Python-first `video-bundle-agent` project, not a `steipete/summarize` fork.
- The Python bundle engine creates local, inspectable evidence bundles and does not call an LLM.
- The user-facing workflow is split into two skill responsibilities:
  - `video-bundle-prep`: prepares reusable bundle evidence, classifies the video after reading text evidence,
    chooses a visual recall strategy, extracts frames, checks readiness, and writes mode-independent
    `report.input.json`.
  - `video-report`: writes final Chinese HTML and preferred long-PNG reports. It can call the prep workflow
    automatically when the user gives it a raw link or local video.
- Two Codex plugin wrappers now exist:
  - `plugins/video-report-agent-local/`: tested local-machine wrapper installed on this workstation.
  - `plugins/video-report-agent/`: portable release wrapper for GitHub-style installs. It has no hard-coded
    workstation paths and expects Codex to run the Python CLI from the cloned repository root.
- Release bootstrap/docs now exist for Windows and macOS: `scripts/bootstrap.ps1`,
  `scripts/bootstrap-macos.sh`, `scripts/install-plugin.ps1`, `scripts/install-plugin-macos.sh`,
  `.env.example`, `docs/install.md`, `docs/configuration.md`, `docs/platform-support.md`,
  `docs/troubleshooting.md`, `docs/release-checklist.md`, and `THIRD_PARTY_NOTICES.md`.
- whisper.cpp release installation is now scripted through `scripts/install-whisper-cpp.ps1` and exposed from
  `scripts/bootstrap.ps1 -WithWhisperCpp`. It downloads the official `ggml-org/whisper.cpp` release runtime
  and default model files (`ggml-large-v3-turbo.bin` plus `ggml-base.bin`) into the configured tool root.
- macOS whisper.cpp installation is scripted through `scripts/install-whisper-cpp-macos.sh` and exposed from
  `scripts/bootstrap-macos.sh --with-whisper-cpp`. It installs Homebrew `whisper-cpp` and downloads the same
  default model files into `~/.local/share/video-report-agent-tools` unless overridden.
- Cookie export helper scripts now accept `-NodePath` and otherwise resolve Node through
  `VIDEO_BUNDLE_AGENT_TOOL_ROOT`, `VIDEO_REPORT_AGENT_TOOL_ROOT`, the original workstation fallback, or
  normal `PATH`.
- macOS cookie export uses `scripts/refresh-cookies-macos.sh`, which reuses the shared Node/CDP exporter and
  supports YouTube, Bilibili, and Xiaohongshu platform presets.
- GitHub publishing baseline now includes GPL-3.0-or-later `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CHANGELOG.md`, `THIRD_PARTY_NOTICES.md`, GitHub issue/PR templates, and CI workflow coverage for
  Windows and macOS.
- The project license is GPL-3.0-or-later because the current Bilibili provider directly depends on
  `bilibili-api-python`, whose observed package metadata is GPL-3.0-or-later.
- Public GitHub repository is configured at `https://github.com/chennw2g/video-report-agent`.
- Public-facing project name is `Video Report Agent`. `video-bundle-agent` is only the internal Python
  CLI/package name for evidence bundle preparation.
- GitHub repository description is Chinese: `视频链接/本地视频 -> 本地证据包 -> 中文图文报告的 AI agent 工作流`.
- `README.md`, `RELEASE_NOTES.md`, and `plugins/video-report-agent/PLUGIN_README.md` now start with Chinese
  public-facing introductions before English notes.
- Local release tag `v0.1.0-alpha.1` has been pushed to GitHub as the first alpha snapshot.
- Current GitHub prerelease is `video-report-agent 0.1.0-alpha.2` at
  `https://github.com/chennw2g/video-report-agent/releases/tag/v0.1.0-alpha.2`.
- `v0.1.0-alpha.2` supersedes alpha.1 with final GitHub Actions cleanup.
- Minimum report evidence remains transcript or audio transcription plus screenshots/keyframes. Comments are
  optional.

## Git State

- Current branch: `main`.
- Current branch tracks `origin/main`.
- Current working tree: clean after the alpha.2 release documentation commit, except for the public-facing
  Chinese intro/name cleanup until committed.
- GitHub remote: `origin` -> `https://github.com/chennw2g/video-report-agent.git`.
- Latest validation in this work session:
  - Public-facing docs cleanup on 2026-06-15 22:48 +08:00:
    - `README.md` title changed from `video-bundle-agent` to `Video Report Agent`.
    - Added Chinese public intro and naming explanation that separates product name from internal CLI name.
    - Added Chinese intro to `RELEASE_NOTES.md` and `plugins/video-report-agent/PLUGIN_README.md`.
    - Updated GitHub repo description through `gh repo edit`.
    - No functional code changed; docs-only update.
  - Release notes follow-up on 2026-06-15 22:38 +08:00:
    - `RELEASE_NOTES.md` and `CHANGELOG.md` now target `0.1.0-alpha.2`.
    - `v0.1.0-alpha.2` is created from the final release documentation commit on `main`.
  - Final GitHub CI release follow-up on 2026-06-15 22:32 +08:00:
    - Latest pushed code commit: `7e55b61 Pin GitHub Actions release tags`.
    - GitHub Actions run `27553571363` completed successfully on `main`.
    - CI passed on both `windows-latest / Python 3.12` and `macos-latest / Python 3.12`.
    - `.github/workflows/ci.yml` now pins current release tags:
      `actions/checkout@v6.0.3`, `actions/setup-python@v6.2.0`, and `astral-sh/setup-uv@v8.2.0`.
    - Earlier commit `a4c5b00` failed because `astral-sh/setup-uv` does not publish a floating `v8`
      action tag; `7e55b61` fixed this by using the exact release tag.
  - GitHub CI follow-up on 2026-06-15 22:13 +08:00:
    - Commit `2c0e58a Use Node 24 for GitHub Actions` passed in GitHub Actions run `27552357917`.
    - That run still emitted a Node 20 deprecation annotation because old action majors were only being
      forced onto Node 24. The later exact-version action update above supersedes this workaround.
  - GitHub publish on 2026-06-15 21:25 +08:00:
    - GitHub CLI authentication succeeded for account `chennw2g`.
    - Created public repository `https://github.com/chennw2g/video-report-agent`.
    - Pushed `main` and tag `v0.1.0-alpha.1`.
    - Published prerelease `v0.1.0-alpha.1`.
  - GitHub publish-readiness update on 2026-06-15 18:20 +08:00:
    - Added GitHub CI workflow, issue templates, PR template, `CONTRIBUTING.md`, `SECURITY.md`,
      `CHANGELOG.md`, `RELEASE_NOTES.md`, `docs/github-publish.md`, and full `LICENSE`.
    - Updated `pyproject.toml` with GPL-3.0-or-later license metadata and classifiers.
    - Replaced third-party notices placeholder with observed direct dependency version/license table.
    - Validation after publish-readiness update:
      - `uv run ruff check`: passed.
      - `uv run pytest`: 69 passed.
      - `uv build` with project-local `UV_CACHE_DIR`: passed and built sdist/wheel.
      - `uv run video-bundle-agent doctor`: warning only; required tools available, optional `tesseract`
        missing.
      - Release and local plugin validators passed.
      - PowerShell script parse check passed.
  - macOS packaging follow-up on 2026-06-15 17:45 +08:00:
    - Added `scripts/bootstrap-macos.sh`, `scripts/install-plugin-macos.sh`,
      `scripts/install-whisper-cpp-macos.sh`, and `scripts/refresh-cookies-macos.sh`.
    - Updated tool discovery so non-Windows defaults to `~/.local/share/video-report-agent-tools` and
      `doctor` can find Homebrew `whisper-cli`.
    - `uv run ruff check`: passed.
    - `uv run pytest tests\test_tool_paths.py tests\test_doctor.py`: 5 passed.
    - Follow-up full validation: `uv run pytest`: 69 passed.
    - Release plugin validator passed for `plugins\video-report-agent`.
    - Bash syntax validation could not run in this Windows session because `bash` returned WSL
      `E_ACCESS_DENIED`; macOS runtime validation still needs to be run on an actual macOS host.
  - Whisper installer follow-up on 2026-06-15 17:23 +08:00:
    - PowerShell parse check passed for `scripts/install-whisper-cpp.ps1` plus bootstrap/plugin/cookie helper
      scripts.
    - `uv run ruff check`: passed.
    - `uv run pytest tests\test_tool_paths.py tests\test_doctor.py`: 5 passed.
    - `uv run python C:\Users\chenn\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\video-report-agent`:
      passed.
    - The installer was not executed to avoid re-downloading large whisper.cpp model files on this machine.
  - Release packaging validation on 2026-06-15 17:02 +08:00:
    - PowerShell parse check passed for `scripts/bootstrap.ps1`, `scripts/install-plugin.ps1`,
      `scripts/install-whisper-cpp.ps1`, and the three cookie refresh scripts.
    - `uv run ruff check`: passed.
    - `uv run pytest`: 69 passed.
    - `uv run video-bundle-agent doctor`: warning only; required tools are available, optional `tesseract`
      is missing.
    - `uv run python C:\Users\chenn\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\video-report-agent`:
      passed.
    - `uv run python C:\Users\chenn\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\video-report-agent-local`:
      passed.
  - `uv run pytest tests/test_report_renderer.py tests/test_visual_recall.py tests/test_xiaohongshu_provider.py`:
    26 passed after the fixed header metric, planned screenshot extraction, and Xiaohongshu parallelization
    changes.
  - `uv run ruff check`: passed.
  - `uv run pytest`: 64 passed.
  - `uv run video-bundle-agent doctor`: warning only; FunASR and whisper.cpp are available, optional
    `tesseract` is missing. `faster-whisper` is no longer part of the checked route.
  - `uv build`: passed and produced ignored local `dist/` wheel/sdist artifacts.
  - `uv run python C:\Users\chenn\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\video-report-agent-local`:
    passed.
  - `uv run python C:\Users\chenn\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py C:\Users\chenn\plugins\video-report-agent-local`:
    passed.
  - Personal marketplace helper reads `personal` from
    `C:\Users\chenn\.agents\plugins\marketplace.json` after rewriting the file as UTF-8 without BOM.
  - `codex plugin add video-bundle-agent-local@personal` was attempted from PowerShell before the rename,
    but WindowsApps returned `Access is denied`; use the Codex app marketplace deeplink or a fresh app
    thread to complete UI-side installation/visibility.
  - The plugin was renamed to `video-report-agent-local` / `Video Report Agent`; the install script removes
    the old `video-bundle-agent-local` entry and directory when refreshing the local plugin.
  - User-side check: the user installed the `Video Report Agent` plugin in Codex and confirmed this local
    packaging version works.
- Global skill sync:
  - `C:\Users\chenn\.codex\skills\video-report\SKILL.md` matches the repo copy.
  - `C:\Users\chenn\.codex\skills\video-report\scripts\render_report.py` matches the repo copy.
  - `C:\Users\chenn\.codex\skills\video-bundle-prep\SKILL.md` matches the repo copy.
- Recent release-related commits before this status entry:
  - `d6f7ee1 Record final release CI status [skip ci]`
  - `7e55b61 Pin GitHub Actions release tags`
  - `a4c5b00 Upgrade GitHub Actions runtime versions`
  - `b4303d7 Record final GitHub CI status`
  - `2c0e58a Use Node 24 for GitHub Actions`
  - `87d8737 Record GitHub publication status`
  - `9a82a0c Add alpha release notes`
  - `2e76dd2 Prepare GitHub release packaging`
  - `ad9dd7b Add local Video Report Agent plugin`
  - `7a927fb Harden video prep and report workflow`

## Provider State

- YouTube: working provider with metadata, yt-dlp chapters when available, subtitles/transcription fallback,
  bounded top comments, audience feedback, retained working media, local thumbnail asset, URL normalization,
  visual recall, timings, and report smoke coverage.
- Bilibili: API-first provider with metadata, native player `view_points` chapters, player subtitle
  extraction through `bilibili-api-python`/`x/player/v2`, playurl media, language-aware local transcription
  fallback, automatic-subtitle comparison transcript when needed, visual recall, top-liked bounded comments,
  local thumbnail asset, `b23.tv` short-link normalization before API collection, timings, and report smoke
  coverage. Danmaku is disabled by default.
- Xiaohongshu: lightweight provider with short-link resolution, HTML note extraction, media download,
  local thumbnail asset, transcription, visual recall, timings, and MediaCrawler-only bounded top-level
  comments through the managed external MediaCrawler runtime.
- Local video: baseline provider now imports a local media file into `raw/media/`, reads ffprobe metadata,
  extracts local audio, uses the shared language-aware transcription route, optionally extracts visual
  recall screenshots, writes `audience_feedback.json` with comments marked unavailable, and produces normal
  bundle/readiness artifacts. It intentionally has no platform comments, online engagement metrics, or
  native chapters unless the user supplies separate source metadata later.

## Report Output State

- Formal report modes are `quick` and `deep`.
- Default mode is `quick`; `deep` is used only when the user explicitly asks for deep analysis.
- `quick` and `deep` share the same HTML/PNG design system. They differ in depth and evidence density.
- Preferred final artifacts are HTML and long PNG. PDF is optional compatibility output only.
- Report visual style v1 is Template D / `Editorial Lab`.
- The renderer is `skills/video-report/scripts/render_report.py`.
- The compact AI multi-dimensional evaluation chart is rendered immediately after the top source information
  and before the video overview.
- Reports use `AI` wording in user-facing section labels, not `Codex`, so the workflow can later run on other
  agent/model shells.
- Footer signature format is `Generated by <agent> (Powered by <model>)`; current default is
  `Generated by CODEX (Powered by GPT-5 Codex)`.
- Header representative images keep their natural aspect ratio and are centered against the text block.
- Header hero visuals now prefer an explicit `hero_visual`, then the local/remote platform thumbnail, then
  body screenshots. Providers try to download `metadata.thumbnail` into `raw/thumbnail/` and write
  `metadata.thumbnail_path` so HTML/long-PNG export does not depend on remote image loading.
- Portrait/vertical hero images now render inside a stable 3:2 horizontal contain box so vertical video
  frames do not stretch the title/header layout.
- The renderer refuses suspected mojibake report content by default when it sees replacement characters or
  long/high-density question-mark runs. Use `--allow-suspect-encoding` only for deliberate diagnostics.
- Final Chinese `report.content.<mode>.json` files must be written through `apply_patch` or a Python writer
  that explicitly uses `encoding="utf-8"`. Do not write Chinese report content through PowerShell pipes,
  here-strings, or `Set-Content`; the renderer's mojibake refusal is only the final guard.
- `timings.json` records stage timing across provider collection, frame extraction, report input
  preparation, and report rendering so slow stages can be diagnosed without external Stopwatch notes.
- Header title and metric values may auto-reduce font size to fit target lines without clipping or ellipses.
- Header metric labels are anchored in the bottom label area so value auto-shrinking does not move labels out
  of alignment.
- Header metric cards must use this fixed order: `平台`, `作者`, `发布时间`, `视频时长`, `播放量`,
  `评论数`, `点赞数`, `分享数`. Do not add a report-type card by default. If a metric is unavailable, show
  `未获取`; do not substitute share count for like count or any other engagement metric.
- Content maps and AI-organized tables are centered by default in the renderer and visual contract.
- User-facing attention notes and renderer-added diagnostics must be Chinese summaries. Raw diagnostic codes
  such as `MEDIA_DOWNLOAD_FAILED` should remain traceable through `diagnostics.json` or the evidence index,
  but should not appear as visible report titles.
- If `source_chapters.json` exists, reports must use native source chapters as the content-map/chapter basis.
  Bilibili `metadata.pages` is page/part metadata only, not original chapters.
- `video-bundle-prep` writes an agent-authored `visual_selection_plan.json` after classification and
  transcript reading. `extract-frames --plan` uses it for coarse baseline sampling plus targeted
  semantic-anchor screenshots; `select-evidence --plan` and `prepare-report --plan` use the same plan for
  semantic selection.
- Planned screenshot extraction uses coarse intervals `low=30s`, `medium=15s`, and `high=8s`. Without a
  plan, the lower-level legacy intervals remain `low=15s`, `medium=5s`, and `high=2s`.
- Xiaohongshu provider now runs MediaCrawler comment collection and local audio transcription in parallel
  after media download, while keeping separate `comments` and `audio_transcription` stage timings.
- Local transcription is language-aware:
  - The provider first cuts a short 16 kHz WAV probe and runs whisper.cpp language detection against actual
    speech audio.
  - Detected Chinese routes to FunASR Paraformer-zh + fsmn-vad + ct-punc + cam++.
  - Detected English and other non-Chinese languages route to whisper.cpp.
  - Platform metadata, title language, and subtitle language are fallback hints only when audio probing fails
    or returns low confidence.
  - YouTube automatic-subtitle comparison uses the same language-aware local transcription selector.
- FunASR speaker output is preserved as anonymous `speaker` cluster ids when `sentence_info[].spk` is present.
- Whisper.cpp model selection remains configurable through `VIDEO_BUNDLE_AGENT_WHISPER_MODEL` or
  `WHISPER_MODEL`. The current local CUDA build makes `ggml-large-v3-turbo.bin` the preferred
  English/other-language quality-and-speed path when CUDA is available; Whisper base remains a CPU-only speed
  fallback candidate.
- Whisper.cpp language detection has its own lightweight model preference. `VIDEO_BUNDLE_AGENT_WHISPER_LANGUAGE_MODEL`
  or `WHISPER_LANGUAGE_MODEL` may override it; otherwise the engine prefers installed `ggml-base.bin`.
- Active whisper.cpp CLI path is now the CUDA build:
  `D:\Workshop\whisper.cpp\v1.8.6-cuda\Release\whisper-cli.exe`.
- CUDA build notes are recorded in `docs/whisper-cuda-build-20260614.md`.
- The old CPU release is preserved at `D:\Workshop\whisper.cpp\v1.8.6\Release`.

## Xiaohongshu Current Finding

Current Xiaohongshu comment status: promoted to MediaCrawler-only. The provider now invokes MediaCrawler's
official `xhs detail` workflow, reads its `jsonl` output, and no longer uses the old bundled local signer path.

Optional exported cookie path for metadata/media requests:

```text
%APPDATA%\video-bundle-agent\xiaohongshu.cookies.txt
```

External MediaCrawler checkout:

```text
D:\W\Codex\external\MediaCrawler
```

MediaCrawler saved login profile:

```text
D:\W\Codex\external\MediaCrawler\browser_data\cdp_xhs_user_data_dir
```

The first MediaCrawler run may open a browser for QR/SMS login. Later runs should reuse this saved profile.
MediaCrawler official `xhs detail` runs are bounded to 180 seconds in the provider. If the run exceeds that,
treat it as login, verification, or platform blocking instead of waiting silently.

Latest successful comment recovery on `http://xhslink.com/o/SRjpwmmZKw`:

- Date: 2026-06-11.
- CDP endpoint: `http://127.0.0.1:9231`.
- CDP cookies were present: 15 Xiaohongshu cookies.
- `selfinfo` returned `code=0`, `success=true`, nickname `Chenn`.
- Parsed note id: `6937701d00000000190273c4`.
- Note detail API succeeded.
- MediaCrawler comment API succeeded with 100 top-level comments.
- Raw output: `outputs/mediacrawler-xhs-comments-SRjpwmmZKw-20260611-221046/`.
- Main project normalization also succeeded with `count_fetched=100`,
  `candidate_source=mediacrawler_xhshow_comment_page`, `selfinfo_ok=true`, and top comment
  `like_count=6196`.
- Normalized output: `outputs/xhs-comments-normalized-SRjpwmmZKw-20260611-221954/comments.json`.
- This validation used the earlier smoke/CDP helper path. The current code has since been changed to call
  MediaCrawler's official detail/jsonl workflow; the newer live smoke below supersedes this older helper
  validation.

Operational rules:

- Prefer MediaCrawler's own saved browser profile for Xiaohongshu comments.
- Do not require manual startup of the old port `9231` dedicated CDP browser in normal runs.
- Do not repeat QR/SMS login loops by default. First let MediaCrawler try its saved login profile.
- If platform risk-control responses return again, keep bundle creation moving and record comments as
  diagnostics rather than blocking the main report.
- Retest note: after exporting fresh cookies from the logged-in CDP browser on 2026-06-11, the original
  `xhs` + builtin local signer path still returned `300011` (`当前账号存在异常，请切换账号后重试`) for
  `SRjpwmmZKw`. This confirms MediaCrawler should remain the only supported comment path.

Historical risk patterns:

- `300011`: account/session risk or interactive verification.
- `461` / `Verifytype=301`: CAPTCHA or verification gate.
- `-100`: login expired.

The provider records these as `PERMISSION_REQUIRED` or `COOKIE_REQUIRED` diagnostics as appropriate.

## Recent Validation

- Latest focused Xiaohongshu comment validation on 2026-06-11 22:25 +08:00:
  - `scripts/start-xiaohongshu-cdp-chrome.ps1 -Port 9231 -StartUrl "http://xhslink.com/o/SRjpwmmZKw"`
    started the dedicated CDP Chrome profile.
  - External MediaCrawler smoke returned 100 top-level comments for `SRjpwmmZKw`.
  - Main project `_fetch_mediacrawler_comments_payload` normalized the same note into standard
    `comments.json` with `count_fetched=100`.
  - A full `analyze` run was not used for the final comment assertion because it entered local video
    transcription before reaching the comment stage; this is not a comment-path failure.
  - Follow-up fix: `_fetch_mediacrawler_comments_payload` now resolves the MediaCrawler raw output
    directory to an absolute path before invoking the external MediaCrawler checkout. This prevents
    repo-relative `--out outputs\...` paths from being interpreted under `D:\W\Codex\external\MediaCrawler`.
  - Relative-output live verification succeeded at
    `outputs/xhs-comments-relative-fix-SRjpwmmZKw-20260611-223217/` with `count_fetched=100`,
    `raw_exists=true`, and top comment `like_count=6196`.
  - Fresh cookies were exported from the logged-in CDP browser to
    `%APPDATA%\video-bundle-agent\xiaohongshu.cookies.txt`.
  - Original `xhs` + builtin local signer retry failed with `300011`; the signer route has now been removed
    from the supported workflow.
- Latest Xiaohongshu workflow refactor on 2026-06-11 23:10 +08:00:
  - `xhs-signer`, `--xhs-sign-url`, `XHS_SIGN_URL`, and `signer.py` were removed.
  - `_fetch_mediacrawler_comments_payload` now calls a project wrapper that runs MediaCrawler's official
    `xhs detail` jsonl workflow in the external MediaCrawler uv environment.
  - MediaCrawler is now checked by `doctor` as an optional but first-class Xiaohongshu comments runtime.
  - `uv run pytest`: 46 passed.
  - `uv run ruff check`: passed.
- Latest full Xiaohongshu official MediaCrawler bundle smoke on 2026-06-11 23:57 +08:00:
  - Input link: `http://xhslink.com/o/2e9GoqicXQ0`.
  - First MediaCrawler run opened its own browser profile and required login. After the user logged in, the
    saved profile worked and MediaCrawler completed the official `xhs detail` jsonl workflow.
  - The provider now handles Xiaohongshu `/login?redirectPath=...` short-link redirects, preserves string
    values that contain `undefined`, and falls back to MediaCrawler `detail_contents_*.jsonl` for note
    metadata/media when the HTML initial state does not expose the target note.
  - Follow-up decision on 2026-06-12 00:02 +08:00: the MediaCrawler provider timeout was shortened from
    900 seconds to 180 seconds because normal saved-login runs completed quickly; longer waits should surface
    as login or platform-gate diagnostics.
  - Output bundle: `outputs/xhs-mediacrawler-2e9GoqicXQ0-20260611-final/`.
  - Source id: `6a2a9e7f000000001c027ff9`; title: `胖东来员工薪资调整`; uploader: `观闻札记`.
  - `check-bundle` result: `report_ready=true`, no blockers, no errors.
  - Evidence counts: 10 transcript segments, 15 screenshot candidates, 100 comments, 12 selected images,
    `report.input.json` generated.
  - Diagnostics: one non-blocking `MEDIA_DOWNLOAD_FAILED` warning for a Xiaohongshu image URL returning
    `404`; downloaded video evidence, transcription, screenshots, comments, and audience feedback are usable.
  - Validation after the provider changes: `uv run pytest tests\test_xiaohongshu_provider.py` passed and
    `uv run ruff check` passed.
- Latest Xiaohongshu comments-only smoke on 2026-06-12 00:31 +08:00:
  - Input link: `http://xhslink.com/o/7o738tnIekj`.
  - Resolved source id: `6a27d2c8000000001603fef3`.
  - MediaCrawler official detail/jsonl comment adapter completed in about 28 seconds using the saved login
    profile; no fresh QR/SMS login was needed.
  - Output: `outputs/xhs-comments-7o738tnIekj-20260612/comments.json`.
  - Result: `count_fetched=23`; comments were normalized and sorted by `like_count` descending. Because the
    platform returned fewer than the requested 100 top-level comments, the result is recorded as a partial
    available sample rather than labelled as Top 100.
  - Top observed comment had `like_count=14` and `reply_count=4`.
- Latest Xiaohongshu full deep-report smoke on 2026-06-12 00:47 +08:00:
  - Input link: `http://xhslink.com/o/8QSjKdRT9Ww`.
  - Output bundle: `outputs/xhs-8QSjKdRT9Ww-deep-20260612/`.
  - Stage-1 analyze completed with metadata, 319 transcript segments, 100 comments, and one non-blocking
    `MEDIA_DOWNLOAD_FAILED` warning for a Xiaohongshu image URL returning `404`.
  - Semantic profile: `深度分析`, with tags `内容运营`, `自媒体增长`, `平台冷启动`, and `方法论`.
  - Visual recall: `high + fixed + max_screenshots=0`, producing 249 screenshot candidates.
  - Readiness after frame extraction: `report_ready=true`, no blockers, no errors.
  - Report preparation selected 16 images and generated `report.input.json`.
  - Deep report artifacts generated:
    - `report.content.deep.json`
    - `report.zh.deep.html`
    - `report.zh.deep.png`
  - Visual QA: long PNG rendered successfully and was nonblank. This source is mostly talking-head video
    with burned-in subtitles, so the report uses screenshots sparingly as timestamp evidence rather than as
    a large visual gallery.
  - Follow-up layout/content fix on 2026-06-12 13:26 +08:00: renderer now detects local portrait hero images
    and uses a 3:2 contain box; the report content rules now say talking-head / low-visual-variation videos
    should not embed body screenshots by default when frames only repeat subtitles or the same speaker pose.
    The same report was re-rendered with only the hero representative frame and no inline body screenshots.
- Latest visual selection plan implementation on 2026-06-12 15:57 +08:00:
  - Added `visual_selection_plan.json` as the agent-authored bridge between semantic intent and deterministic
    screenshot selection.
  - `select-evidence` and `prepare-report` accept `--plan visual_selection_plan.json`; no-plan behavior remains
    backward compatible.
  - `report.input.json.selected_evidence` now records selection strategy, body screenshot policy, compact plan
    summary, and per-image anchor metadata when a plan is used.
  - Focused validation: `uv run pytest tests\test_evidence_selection.py tests\test_report_input.py` passed
    with 6 tests.
  - Full validation after docs/skill sync: `uv run pytest` passed with 48 tests and `uv run ruff check`
    passed.
  - Project `video-bundle-prep` and `video-report` skill files were synced to
    `C:\Users\chenn\.codex\skills\...`; SHA256 hashes matched the project files after sync.
  - CLI flow smoke passed on `outputs/visual-selection-plan-cli-smoke/`:
    `select-evidence --plan visual_selection_plan.json` and `prepare-report --plan visual_selection_plan.json`
    both completed, `report.input.json` was valid UTF-8 JSON, and the first selected image used
    `selection_strategy=plan_guided`, `selection_reasons=["semantic_anchor"]`, timestamp `20.0`.
- Latest ASR runtime update on 2026-06-12 17:22 +08:00:
  - Downloaded whisper.cpp `ggml-large-v3-turbo.bin` to `D:\Workshop\whisper.cpp\models\`.
  - Changed whisper.cpp model discovery to prefer env override, then turbo/large, medium, small, and base.
  - Installed optional `funasr` extra in the project environment: `funasr 1.3.9`,
    `torch 2.11.0+cu128`, `torchaudio 2.11.0+cu128`.
  - Verified FunASR imports successfully and PyTorch CUDA is available on
    `NVIDIA GeForce RTX 5060 Laptop GPU`.
  - Verified `whisper_cpp_model_path()` selects `ggml-large-v3-turbo.bin` with no environment override.
  - Validation: `uv run video-bundle-agent doctor` reports FunASR available; `uv run pytest` passed with
    50 tests; `uv run ruff check` passed.
- Latest ASR benchmark update on 2026-06-12 19:45 +08:00:
  - Added `scripts/asr_benchmark.py` for local same-audio ASR comparison. It writes `.segments.json`, `.txt`,
    `.srt`, `.timed.txt`, and `timings.json`. Detailed benchmark notes are in
    `docs/asr-benchmark-20260612.md`.
  - Bilibili Chinese benchmark source: `https://b23.tv/eViSC63`, `BV1wEVo6eEYv`, duration 2600.4 seconds.
    Outputs are under `outputs/asr-benchmark-20260612/bilibili_full/`.
    - Whisper large-v3-turbo: 1617.34 seconds, RTF 0.622, 1664 segments.
    - SenseVoiceSmall + fsmn-vad + cam++: 118.52 seconds, RTF 0.046, 143 normalized segments.
    - Paraformer-zh + fsmn-vad + ct-punc + cam++: 105.47 seconds, RTF 0.041, 405 normalized segments.
    - Initial read: Paraformer-zh is the best Chinese report-input candidate among the FunASR pair because
      it has stronger punctuation/paragraph usability; SenseVoiceSmall keeps useful emotion/language tags but
      segments more coarsely without an external punc model. Whisper is much slower on this CPU path.
  - YouTube English benchmark source: `https://youtu.be/AOEr5FrW-lY`, `AOEr5FrW-lY`, duration 1238.0
    seconds. Outputs are under `outputs/asr-benchmark-20260612/youtube_full/`.
    - Whisper large-v3-turbo: 802.58 seconds, RTF 0.648, 340 segments.
    - SenseVoiceSmall + fsmn-vad + cam++: 55.64 seconds, RTF 0.045, 146 normalized segments.
    - Paraformer-zh + fsmn-vad + ct-punc + cam++: 63.66 seconds, RTF 0.051, 158 normalized segments.
    - Initial read: Whisper large-v3-turbo is clearly best for English accuracy and punctuation. The two
      Chinese-oriented FunASR paths are fast but introduce word breaks, wrong names, or mixed-language noise.
  - Installed project Python dependency `yt-dlp[default]` so PyPI yt-dlp includes `yt-dlp-ejs`. YouTube format
    extraction for `AOEr5FrW-lY` required `--js-runtimes node`; without EJS it returned only storyboard
    images and `n challenge solving failed`.
  - Follow-up comparison against YouTube official captions on `AOEr5FrW-lY` stripped JSON3 HTML tags before
    tokenization and produced: Whisper large-v3-turbo WER 2.01% (56 suspected token errors),
    SenseVoiceSmall WER 11.32% (315), Paraformer-zh WER 21.09% (587). This confirms Whisper remains the
    English/default-quality path, while the Chinese-oriented FunASR models are not suitable as English primary.
  - Additional Whisper base English follow-up used the already-installed `ggml-base.bin`: 94.42 seconds,
    RTF 0.076, WER 2.23% (62 suspected token errors) against the same official captions. This makes Whisper
    base the current English speed candidate, while turbo remains the quality candidate.
  - Quantized Whisper turbo q5_0 follow-up used `ggml-large-v3-turbo-q5_0.bin`: 977.07 seconds, RTF 0.789,
    WER 2.44% (68 suspected token errors). On the current CPU-only whisper.cpp build, q5_0 is smaller but
    slower than unquantized turbo and not competitive with Whisper base.
  - Fixed ASR benchmark FunASR normalization so `sentence_info[].spk` is preserved as `speaker` in standard
    segments. A Bilibili Paraformer speaker-check run produced 1,323 segments with anonymous speaker-cluster
    counts: `0` = 369, `1` = 942, `2` = 6, `3` = 6.
  - The Chinese Bilibili source did not expose an authoritative subtitle in benchmark artifacts, so Chinese
    accuracy remains reference-free: Paraformer-zh is still the most usable Chinese candidate by speed and
    punctuation, but proper nouns/domain terms need a flagged comparison route before production defaulting.
  - The Bilibili ASR benchmark audio was an ad hoc same-audio extraction for model comparison, not a production
    provider workflow run. Normal Bilibili analysis remains `bilibili-api-python` primary with `yt-dlp` only
    as fallback.
- Latest ASR language-routing update on 2026-06-13 14:14 +08:00:
  - Added a pre-transcription language probe: the engine cuts a short 16 kHz WAV sample, runs whisper.cpp
    `--detect-language`, and uses the detected speech language to choose FunASR for Chinese or whisper.cpp
    for non-Chinese audio.
  - Platform metadata, title language, and subtitle language are now fallback hints rather than the primary
    routing source. They are also used when the probe returns a low-confidence language. This avoids
    misrouting Bilibili/YouTube/Xiaohongshu videos whose spoken language differs from title or platform metadata.
  - Language-probe artifacts are retained in the bundle manifest when available:
    `language_probe_audio_path` and `language_probe_output_path`.
  - `transcript.segments.json` can include a `language_detection` object with engine, detected language,
    confidence, `accepted`, probe duration, sample path, model path, and raw output path.
  - Language-probe smoke on existing benchmark audio detected `zh` with confidence `0.997134` for
    `bilibili_16k.wav` and `en` with confidence `0.981981` for `youtube_16k.wav`.
  - Removed `faster-whisper` from `doctor`; it is not an adopted route because the project is staying with
    official whisper.cpp plus FunASR.
  - Synced `skills/video-bundle-prep/SKILL.md` to
    `C:\Users\chenn\.codex\skills\video-bundle-prep\SKILL.md`; SHA256 hashes match.
  - Validation: `uv run pytest` passed with 57 tests, `uv run ruff check` passed, and
    `uv run video-bundle-agent doctor` returned warning only for missing optional `tesseract`.
- Latest whisper.cpp CUDA build on 2026-06-14 18:50 +08:00:
  - Installed Visual Studio Build Tools 2022 C++ toolchain and Windows SDK 10.0.26100.0.
  - Installed CMake 3.25.0 and Ninja 1.13.0 into the project `.venv` with `uv pip install cmake ninja`.
  - Built official `ggml-org/whisper.cpp` tag `v1.8.6` from source at
    `D:\Workshop\whisper.cpp\src-v1.8.6`, with `GGML_CUDA=ON`, `GGML_CUDA_NCCL=OFF`, and
    `CMAKE_CUDA_ARCHITECTURES=120`. CMake converted this to `120a` for the RTX 5060 Laptop GPU.
  - CUDA Toolkit was assembled from NVIDIA official 13.2.1 redist packages under
    `D:\Workshop\CUDA\v13.2.1-redist`; this avoids replacing the system CUDA/PATH globally.
  - Packaged CUDA runtime is at `D:\Workshop\whisper.cpp\v1.8.6-cuda\Release`.
  - `src/video_bundle_agent/tools/paths.py` now prefers
    `D:\Workshop\whisper.cpp\v1.8.6-cuda\Release\whisper-cli.exe` before the old CPU release.
  - Synced updated `skills/video-bundle-prep/SKILL.md` to
    `C:\Users\chenn\.codex\skills\video-bundle-prep\SKILL.md`; SHA256 hashes match.
  - Direct CUDA smoke detected `NVIDIA GeForce RTX 5060 Laptop GPU`, compute capability `12.0`, and used
    `CUDA0` backend. The 60-second Chinese language probe detected `zh` with confidence about `0.997`.
  - Full English same-audio benchmark on `outputs/asr-benchmark-20260612/youtube_16k.wav` with
    `ggml-large-v3-turbo.bin` completed in `38.19` seconds for `1238.04` seconds of audio, RTF `0.03085`.
    WER against the YouTube official JSON3 subtitle was `1.29%` (`36` token errors over `2,783` reference
    tokens). Prior CPU turbo result was `802.58` seconds, RTF `0.648`, WER `2.01%`.
  - Output benchmark directory:
    `outputs/asr-benchmark-20260614-gpu-whisper/youtube_turbo_gpu/`.
  - Validation: `find_executable("whisper")` resolves to the CUDA release; `uv run video-bundle-agent doctor`
    reports the CUDA release path and only warns for missing optional `tesseract`; `uv run pytest` passed with
    58 tests and `uv run ruff check` passed.
- Latest workflow hardening on 2026-06-14 22:18 +08:00:
  - Added `timings.json` stage timing for provider collection, `extract-frames`, `prepare-report`, and
    `render_report.py`.
  - Added provider URL normalization for YouTube short forms, Bilibili `b23.tv`, and Xiaohongshu short-link
    resolution reuse. Bilibili now normalizes short links before the API metadata/comment path, avoiding the
    earlier `aid`-missing comment failure pattern.
  - Providers now try to download `metadata.thumbnail` to `raw/thumbnail/`, write `metadata.thumbnail_path`,
    and list it as a bundle artifact. The report renderer now prefers explicit `hero_visual`, then platform
    thumbnail, then body screenshots for the top visual.
  - `render_report.py` now refuses suspected encoding-damaged content by default so PowerShell mojibake or
    question-mark-corrupted Chinese JSON does not silently produce a bad report.
  - Added a project rule that mode-specific Chinese report content JSON must be written through UTF-8-safe
    paths, not PowerShell text pipes or `Set-Content`.
  - Project `video-bundle-prep` and `video-report` skill files were synced to
    `C:\Users\chenn\.codex\skills\...`; `video-report/scripts/render_report.py` was also synced.
    SHA256 hashes matched after sync.
  - Validation: `uv run ruff check` passed; `uv run pytest` passed with 61 tests.
- Latest Windows UTF-8 hardening on 2026-06-14 22:54 +08:00:
  - Created a current-user Windows PowerShell profile at
    `C:\Users\chenn\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`.
  - New Windows PowerShell sessions now set code page 65001, console input/output encoding, PowerShell
    `$OutputEncoding`, `PYTHONIOENCODING=utf-8`, and `PYTHONUTF8=1`.
  - Set PowerShell execution policy for `CurrentUser` to `RemoteSigned` so the profile can load. Machine
    policy and local machine policy were not changed.
  - Recorded the change and rollback notes in `D:\W\Codex\windows-change-log.md`.
  - Verified a new PowerShell session reports UTF-8 input/output encodings, `PYTHONIOENCODING=utf-8`,
    `PYTHONUTF8=1`, and active code page 65001.
- Latest general audit on 2026-06-11 13:57 +08:00:
  - `git status --short --branch`: clean `main`.
  - `uv run pytest`: 48 passed.
  - `uv run ruff check`: passed.
  - `uv run video-bundle-agent doctor`: warning only. Required tools are available; optional `tesseract`
    was missing. The old faster-whisper optional check has since been removed.
  - Global `C:\Users\chenn\.codex\skills\video-bundle-prep` and `video-report` matched the project skill
    files by hash.
  - Existing readiness checks:
    - YouTube `outputs/youtube-csT9MTHQR5M-20260606-114149`: ready, 326 transcript segments, 80 screenshots,
      100 comments.
    - Bilibili `outputs/bilibili-report-BV1xuVC6AEbg-auth-20260606-173936`: ready, 1549 transcript
      segments, 1420 screenshots, 100 comments.
    - Xiaohongshu `outputs/xiaohongshu-smoke-20260606-195932`: ready with metadata, transcript, and
      screenshots; older comments were missing and recorded as a warning.
- Latest provider/report audit on 2026-06-08 21:15 +08:00:
  - YouTube chapter normalization writes yt-dlp `chapters` to `source_chapters.json` when available.
  - Bilibili original chapter smoke on `BV1xuVC6AEbg` returned 10 native chapters and backfilled
    `source_chapters.json`.
  - Long PNG export smoke generated
    `outputs/bilibili-report-BV1xuVC6AEbg-auth-20260606-173936/report.zh.deep.body.png`.
  - CLI entrypoints checked at that time: `doctor`, `analyze`, `extract-frames`, `check-bundle`,
    `select-evidence`, `prepare-report`, `compare-transcripts`, and the now-removed `xhs-signer`.
  - Core docs and both skill files were valid UTF-8. A later 2026-06-14 current-user PowerShell profile
    update now configures new PowerShell sessions for UTF-8 by default.

## Known Gaps

- `tesseract` is not installed. OCR remains optional in the current phase.
- `faster-whisper` is intentionally not used or checked. Current production local transcription uses the CUDA
  `whisper.cpp` CLI at `D:\Workshop\whisper.cpp\v1.8.6-cuda\Release\whisper-cli.exe` for English and other
  non-Chinese audio, with `ggml-large-v3-turbo.bin` as the preferred local model. Chinese audio uses FunASR.
- Release packaging baseline is present for Windows and macOS, but final public-release hardening still needs
  validation from clean Windows and macOS clones plus a full dependency/license review. Windows whisper.cpp
  CPU binary/model installation is scripted; macOS uses Homebrew `whisper-cpp` plus scripted model downloads.
  CUDA installs still depend on compatible NVIDIA runtime availability on the target machine.
- Copying selected screenshots into `screenshots/selected/`, OCR-based slide filtering, complex visual
  deduplication, sharpness/brightness scoring, and agent-assisted final body-image placement remain future
  work.

## Next Decisions

- Validate the portable release plugin and bootstrap path from clean Windows and macOS checkouts before
  publishing to GitHub.
- Run a macOS smoke when a macOS host is available: `bash scripts/bootstrap-macos.sh --install-tools
  --with-playwright --with-whisper-cpp --install-plugin`, `uv run video-bundle-agent doctor`, and at least
  one YouTube or local-video bundle/report flow.
- Decide whether the first public release should default `bootstrap.ps1 -WithWhisperCpp` to CPU for maximum
  compatibility or document CUDA backend selection more prominently for NVIDIA users.
- Keep Xiaohongshu comments on the MediaCrawler official detail/jsonl path.
- Avoid repeated QR/SMS debugging unless MediaCrawler's saved profile actually expires or returns a platform
  verification gate.
- Treat MediaCrawler as a managed external runtime; keep other Xiaohongshu projects as references first.
