import os
import shutil
from pathlib import Path

WORKSHOP_ROOT = Path("D:/Workshop")


def _path_entries() -> list[Path]:
    return [Path(entry) for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]


def candidate_paths(tool: str) -> list[Path]:
    exe = tool if tool.lower().endswith(".exe") else f"{tool}.exe"
    candidates: list[Path] = []

    workshop_candidates = {
        "uv": [
            WORKSHOP_ROOT / "uv" / "uv.exe",
            Path.home() / ".local" / "bin" / "uv.exe",
            Path.home() / "AppData" / "Roaming" / "Python" / "Python312" / "Scripts" / "uv.exe",
            Path.home()
            / "AppData"
            / "Local"
            / "Programs"
            / "Python"
            / "Python312"
            / "Scripts"
            / "uv.exe",
        ],
        "ffmpeg": [
            WORKSHOP_ROOT / "FFmpeg" / "ffmpeg-8.1.1-full_build" / "bin" / "ffmpeg.exe",
            WORKSHOP_ROOT / "FFmpeg" / "bin" / "ffmpeg.exe",
        ],
        "ffprobe": [
            WORKSHOP_ROOT / "FFmpeg" / "ffmpeg-8.1.1-full_build" / "bin" / "ffprobe.exe",
            WORKSHOP_ROOT / "FFmpeg" / "bin" / "ffprobe.exe",
        ],
        "yt-dlp": [
            WORKSHOP_ROOT / "yt-dlp" / "yt-dlp.exe",
        ],
        "node": [
            WORKSHOP_ROOT / "NodeJS" / "node.exe",
        ],
        "tesseract": [
            WORKSHOP_ROOT / "Tesseract-OCR" / "tesseract.exe",
            Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        ],
        "whisper": [
            WORKSHOP_ROOT / "whisper.cpp" / "v1.8.6" / "Release" / "whisper-cli.exe",
            WORKSHOP_ROOT / "whisper.cpp" / "Release" / "whisper-cli.exe",
        ],
        "chrome": [
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
        ],
        "chromium": [
            WORKSHOP_ROOT / "Chromium" / "chrome.exe",
        ],
    }
    candidates.extend(workshop_candidates.get(tool, []))

    found = shutil.which(tool)
    if found:
        candidates.append(Path(found))

    for entry in _path_entries():
        candidates.append(entry / exe)
        candidates.append(entry / tool)

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate).lower()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def find_executable(tool: str) -> Path | None:
    for candidate in candidate_paths(tool):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None
