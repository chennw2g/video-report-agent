import os
import shutil
from pathlib import Path

DEFAULT_WORKSHOP_ROOT = (
    Path("D:/Workshop")
    if os.name == "nt"
    else Path.home() / ".local" / "share" / "video-report-agent-tools"
)
WORKSHOP_ROOT = Path(
    os.environ.get("VIDEO_BUNDLE_AGENT_TOOL_ROOT")
    or os.environ.get("VIDEO_REPORT_AGENT_TOOL_ROOT")
    or DEFAULT_WORKSHOP_ROOT
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def mediacrawler_path_candidates() -> list[Path]:
    configured = os.environ.get("XHS_MEDIACRAWLER_PATH")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            project_root() / "external" / "MediaCrawler",
            Path.cwd() / "external" / "MediaCrawler",
            Path("D:/W/Codex/external/MediaCrawler"),
        ]
    )

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate).lower()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def mediacrawler_path() -> Path:
    for candidate in mediacrawler_path_candidates():
        if (candidate / "main.py").exists() and (candidate / "pyproject.toml").exists():
            return candidate
    return mediacrawler_path_candidates()[0]


def _path_entries() -> list[Path]:
    return [Path(entry) for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]


def candidate_paths(tool: str) -> list[Path]:
    aliases = [tool]
    if tool == "whisper":
        aliases.append("whisper-cli")
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
            WORKSHOP_ROOT / "whisper.cpp" / "v1.8.6-cuda" / "Release" / "whisper-cli.exe",
            WORKSHOP_ROOT / "whisper.cpp" / "v1.8.6-blas" / "Release" / "whisper-cli.exe",
            WORKSHOP_ROOT / "whisper.cpp" / "v1.8.6" / "Release" / "whisper-cli.exe",
            WORKSHOP_ROOT / "whisper.cpp" / "Release" / "whisper-cli.exe",
            WORKSHOP_ROOT / "whisper.cpp" / "bin" / "whisper-cli",
            WORKSHOP_ROOT / "whisper.cpp" / "v1.8.6" / "bin" / "whisper-cli",
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

    for alias in aliases:
        found = shutil.which(alias)
        if found:
            candidates.append(Path(found))

    for entry in _path_entries():
        for alias in aliases:
            alias_exe = alias if alias.lower().endswith(".exe") else f"{alias}.exe"
            candidates.append(entry / alias_exe)
            candidates.append(entry / alias)

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
