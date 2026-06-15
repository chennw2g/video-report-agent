# Third-Party Notices

This repository wraps external tools and Python libraries. It does not vendor platform login state,
cookies, raw downloads, generated bundles, generated reports, or third-party source checkouts by default.

License metadata below reflects the current locked development environment at the time this file was
updated. Transitive dependency licenses are resolved by the package manager and should be reviewed again
before a stable tagged release.

## Direct Python Dependencies

| Dependency | Observed version | Observed license metadata | Upstream |
| --- | ---: | --- | --- |
| `bilibili-api-python` | 17.4.1 | GPL-3.0-or-later | https://github.com/Nemo2011/bilibili-api |
| `curl-cffi` | 0.15.0 | See upstream metadata | https://github.com/lexiforest/curl_cffi |
| `httpx` | 0.28.1 | BSD-3-Clause | https://github.com/encode/httpx |
| `lxml` | 6.1.1 | BSD-3-Clause | https://lxml.de/ |
| `playwright` | 1.60.0 | See upstream metadata | https://github.com/microsoft/playwright-python |
| `pydantic` | 2.13.4 | See upstream metadata | https://github.com/pydantic/pydantic |
| `requests` | 2.34.2 | Apache-2.0 | https://requests.readthedocs.io |
| `typer` | 0.26.7 | See upstream metadata | https://github.com/fastapi/typer |
| `xhs` | 0.2.13 | MIT | https://github.com/ReaJason/xhs |
| `yt-dlp` | 2026.6.9 | See upstream metadata | https://github.com/yt-dlp/yt-dlp |

## Optional Python Dependencies

| Dependency | Observed version | Observed license metadata | Upstream |
| --- | ---: | --- | --- |
| `funasr` | 1.3.9 | MIT | https://github.com/modelscope/FunASR |
| `torch` | 2.11.0+cu128 | BSD-3-Clause | https://pytorch.org |
| `torchaudio` | 2.11.0+cu128 | BSD-style classifier | https://github.com/pytorch/audio |

## Development Dependencies

| Dependency | Observed version | Observed license metadata | Upstream |
| --- | ---: | --- | --- |
| `pytest` | 9.0.3 | See upstream metadata | https://docs.pytest.org/ |
| `ruff` | 0.15.16 | See upstream metadata | https://docs.astral.sh/ruff/ |

## External Runtime Tools

- FFmpeg/ffprobe for media probing, audio extraction, and frame extraction.
- Node.js for cookie export helpers and some yt-dlp JavaScript signature paths.
- MediaCrawler as an external checkout for Xiaohongshu comments. It is installed under `external/` by
  bootstrap scripts when requested and is not vendored into this repository.
- Playwright/Chromium for MediaCrawler and optional browser automation workflows.
- whisper.cpp for language probing and non-Chinese local transcription. Windows installer scripts download
  runtime archives from `ggml-org/whisper.cpp` GitHub releases and model files from
  `ggerganov/whisper.cpp` on Hugging Face. macOS installer scripts use the Homebrew `whisper-cpp` formula
  for the runtime and the same Hugging Face model repository for `.bin` models.
- Tesseract as an optional OCR dependency.

## Repository License Choice

The project is licensed as GPL-3.0-or-later because the current Bilibili provider directly depends on
`bilibili-api-python`, whose observed package metadata is GPL-3.0-or-later. If a future release needs a
more permissive project license, the GPL dependency must be isolated, made optional with clear distribution
boundaries, or replaced.
