from __future__ import annotations

from video_bundle_agent.tools.paths import find_executable


def ocr_tool_status() -> dict[str, object]:
    tesseract = find_executable("tesseract")
    if tesseract:
        return {"available": True, "tool": "tesseract", "path": str(tesseract)}
    return {"available": False, "tool": None, "path": None}
