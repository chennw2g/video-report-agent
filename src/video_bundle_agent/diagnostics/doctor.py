from __future__ import annotations

import importlib.util
import sys
from importlib import metadata
from pathlib import Path

from video_bundle_agent.diagnostics.models import DoctorReport, ToolCheck
from video_bundle_agent.tools.paths import find_executable
from video_bundle_agent.tools.process import CommandError, run_command


def _version_from_command(path: Path, args: list[str]) -> str | None:
    try:
        completed = run_command([path, *args], timeout_seconds=15)
    except (CommandError, OSError, TimeoutError):
        return None
    first_line = (completed.stdout or completed.stderr).splitlines()
    return first_line[0].strip() if first_line else None


def _check_executable(
    name: str,
    *,
    required: bool,
    version_args: list[str] | None = None,
) -> ToolCheck:
    path = find_executable(name)
    if not path:
        status = "error" if required else "warning"
        return ToolCheck(
            name=name,
            required=required,
            available=False,
            status=status,
            message=f"{name} was not found.",
        )

    args = ["--version"] if version_args is None else version_args
    version = _version_from_command(path, args) if args else None
    return ToolCheck(
        name=name,
        required=required,
        available=True,
        status="ok",
        version=version,
        path=str(path),
        message=f"{name} is available.",
    )


def _check_python() -> ToolCheck:
    return ToolCheck(
        name="python",
        required=True,
        available=True,
        status="ok",
        version=sys.version.split()[0],
        path=sys.executable,
        message="python is available.",
    )


def _check_python_module(name: str, *, required: bool = False) -> ToolCheck:
    spec = importlib.util.find_spec(name.replace("-", "_"))
    if not spec:
        return ToolCheck(
            name=name,
            required=required,
            available=False,
            status="error" if required else "warning",
            message=f"Python module {name} was not found.",
        )
    try:
        version = metadata.version(name)
    except metadata.PackageNotFoundError:
        version = None
    return ToolCheck(
        name=name,
        required=required,
        available=True,
        status="ok",
        version=version,
        path=spec.origin,
        message=f"Python module {name} is available.",
    )


def run_doctor() -> DoctorReport:
    tools = [
        _check_python(),
        _check_executable("uv", required=True),
        _check_executable("ffmpeg", required=True, version_args=["-version"]),
        _check_executable("ffprobe", required=True, version_args=["-version"]),
        _check_executable("yt-dlp", required=True),
        _check_executable("tesseract", required=False),
        _check_executable("whisper", required=False, version_args=[]),
        _check_python_module("faster-whisper", required=False),
        _check_python_module("xhs", required=False),
        _check_python_module("playwright", required=False),
    ]

    chrome = _check_executable("chrome", required=False, version_args=[])
    chromium = _check_executable("chromium", required=False, version_args=[])
    if chrome.available:
        tools.append(chrome)
    else:
        tools.append(chromium)

    if any(tool.status == "error" for tool in tools):
        status = "error"
    elif any(tool.status == "warning" for tool in tools):
        status = "warning"
    else:
        status = "ok"

    return DoctorReport(status=status, tools=tools)
