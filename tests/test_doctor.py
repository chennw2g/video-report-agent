from video_bundle_agent.diagnostics.doctor import run_doctor


def test_doctor_reports_required_tool_names() -> None:
    report = run_doctor()
    names = {tool.name for tool in report.tools}

    assert {"python", "uv", "ffmpeg", "ffprobe", "yt-dlp"}.issubset(names)
    assert report.status in {"ok", "warning", "error"}
