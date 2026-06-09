from __future__ import annotations

import subprocess
from pathlib import Path


class CommandError(RuntimeError):
    def __init__(self, message: str, returncode: int, stdout: str, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run_command(
    args: list[str | Path],
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 120,
) -> subprocess.CompletedProcess[str]:
    command = [str(arg) for arg in args]
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise CommandError(
            f"Command failed with exit code {completed.returncode}: {command[0]}",
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )
    return completed
