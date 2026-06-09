from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from video_bundle_agent.tools.paths import find_executable
from video_bundle_agent.tools.process import run_command


class YtDlpUnavailable(FileNotFoundError):
    pass


def yt_dlp_path() -> Path:
    path = find_executable("yt-dlp")
    if not path:
        raise YtDlpUnavailable("yt-dlp was not found")
    return path


def _js_runtime_args() -> list[str | Path]:
    node = find_executable("node")
    if not node:
        return []
    return ["--js-runtimes", f"node:{node}"]


def dump_single_json(
    url: str,
    *,
    write_comments: bool = False,
    max_comments: int = 100,
    comment_sort: str = "top",
    cookies: Path | None = None,
    cookies_from_browser: str | None = None,
    timeout_seconds: int = 240,
) -> dict[str, Any]:
    command: list[str | Path] = [
        yt_dlp_path(),
        "--dump-single-json",
        "--skip-download",
        "--no-playlist",
        "--no-warnings",
    ]
    command.extend(_js_runtime_args())
    if cookies:
        command.extend(["--cookies", cookies])
    if cookies_from_browser:
        command.extend(["--cookies-from-browser", cookies_from_browser])
    if write_comments:
        command.extend(
            [
                "--write-comments",
                "--extractor-args",
                f"youtube:comment_sort={comment_sort};max_comments={max_comments}",
            ]
        )
    else:
        command.append("--no-write-comments")
    command.append(url)

    completed = run_command(command, timeout_seconds=timeout_seconds)
    return json.loads(completed.stdout)


def write_subtitles(
    url: str,
    output_dir: Path,
    source_id: str | None = None,
    *,
    cookies: Path | None = None,
    cookies_from_browser: str | None = None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = "%(id)s.%(ext)s" if not source_id else f"{source_id}.%(ext)s"
    command: list[str | Path] = [
        yt_dlp_path(),
        "--skip-download",
        "--no-playlist",
        "--no-warnings",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "en.*,en,zh.*,zh-Hans.*,zh-Hant.*,zh",
        "--sub-format",
        "json3/vtt/best",
        "--paths",
        output_dir,
        "--output",
        output_template,
    ]
    command.extend(_js_runtime_args())
    if cookies:
        command.extend(["--cookies", cookies])
    if cookies_from_browser:
        command.extend(["--cookies-from-browser", cookies_from_browser])
    command.append(url)
    run_command(command, timeout_seconds=240)
    return sorted(
        [
            path
            for path in output_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".json3", ".vtt", ".srv1", ".srv2", ".srv3"}
        ]
    )


def download_working_video(
    url: str,
    output_dir: Path,
    *,
    source_id: str,
    max_height: int = 1080,
    cookies: Path | None = None,
    cookies_from_browser: str | None = None,
    timeout_seconds: int = 1800,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = f"{source_id}.%(height)sp.%(ext)s"
    command: list[str | Path] = [
        yt_dlp_path(),
        "--no-playlist",
        "--no-warnings",
        "--format",
        f"bestvideo[height<={max_height}]/best[height<={max_height}]/bestvideo/best",
        "--paths",
        output_dir,
        "--output",
        output_template,
    ]
    command.extend(_js_runtime_args())
    if cookies:
        command.extend(["--cookies", cookies])
    if cookies_from_browser:
        command.extend(["--cookies-from-browser", cookies_from_browser])
    command.append(url)

    before = {path.resolve() for path in output_dir.iterdir() if path.is_file()}
    run_command(command, timeout_seconds=timeout_seconds)
    candidates = [
        path
        for path in output_dir.iterdir()
        if path.is_file()
        and path.resolve() not in before
        and path.name.startswith(f"{source_id}.")
        and path.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov"}
    ]
    if not candidates:
        candidates = [
            path
            for path in output_dir.iterdir()
            if path.is_file()
            and path.name.startswith(f"{source_id}.")
            and path.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov"}
        ]
    if not candidates:
        raise FileNotFoundError("yt-dlp did not produce a working video file")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def download_working_audio(
    url: str,
    output_dir: Path,
    *,
    source_id: str,
    cookies: Path | None = None,
    cookies_from_browser: str | None = None,
    timeout_seconds: int = 1800,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = f"{source_id}.%(ext)s"
    command: list[str | Path] = [
        yt_dlp_path(),
        "--no-playlist",
        "--no-warnings",
        "--format",
        "bestaudio/best",
        "--paths",
        output_dir,
        "--output",
        output_template,
    ]
    command.extend(_js_runtime_args())
    if cookies:
        command.extend(["--cookies", cookies])
    if cookies_from_browser:
        command.extend(["--cookies-from-browser", cookies_from_browser])
    command.append(url)

    before = {path.resolve() for path in output_dir.iterdir() if path.is_file()}
    run_command(command, timeout_seconds=timeout_seconds)
    candidates = [
        path
        for path in output_dir.iterdir()
        if path.is_file()
        and path.resolve() not in before
        and path.name.startswith(f"{source_id}.")
        and path.suffix.lower() in {".m4a", ".mp3", ".ogg", ".opus", ".webm", ".wav", ".flac"}
    ]
    if not candidates:
        candidates = [
            path
            for path in output_dir.iterdir()
            if path.is_file()
            and path.name.startswith(f"{source_id}.")
            and path.suffix.lower() in {".m4a", ".mp3", ".ogg", ".opus", ".webm", ".wav", ".flac"}
        ]
    if not candidates:
        raise FileNotFoundError("yt-dlp did not produce a working audio file")
    return max(candidates, key=lambda path: path.stat().st_mtime)
