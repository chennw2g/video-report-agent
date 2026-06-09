# Environment Cleanup

Date: 2026-06-06

## Removed summarize-specific state

- Removed `C:\Users\chenn\.summarize`.
- Removed `C:\Users\chenn\AppData\Roaming\summarize`.
- Removed the dedicated Chrome profile used for YouTube cookie smoke testing.
- Removed the exported YouTube cookies file under `%APPDATA%\summarize`.
- Closed Chrome processes that were using `summarize\chrome-youtube-profile` or `remote-debugging-port=9224`.

## Checked and not found

- No global npm `@steipete/summarize` package was installed.
- No `summarize` or `summarizer` command was found on PATH.
- No Windows Scheduled Task matching `summarize` or `steipete` was found.
- No Windows service matching `summarize` or `steipete` was found.
- No persistent `SUMMARIZE_*` environment variables were found in HKCU or HKLM.
- No summarize startup item or Run-key entry was found.

## Preserved general tools

- Node.js and pnpm/Corepack
- Python and uv, if present
- ffmpeg and ffprobe
- yt-dlp
- Chrome
- whisper.cpp, because it is a general local transcription tool and may be reused

## Notes

The project root now uses a fresh local Git repository with no summarize upstream remote.
The previous summarize fork is kept only as a local reference archive under `archives/`.
