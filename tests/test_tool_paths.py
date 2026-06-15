from pathlib import Path

from video_bundle_agent.tools.paths import (
    WORKSHOP_ROOT,
    candidate_paths,
    mediacrawler_path,
    mediacrawler_path_candidates,
)


def test_workshop_node_is_preferred_before_path_candidates() -> None:
    candidates = candidate_paths("node")

    assert candidates[0] == WORKSHOP_ROOT / "NodeJS" / "node.exe"
    assert Path("WindowsApps") not in candidates[0].parts


def test_cuda_whisper_is_preferred_before_cpu_release() -> None:
    candidates = candidate_paths("whisper")

    assert candidates[0] == (
        WORKSHOP_ROOT / "whisper.cpp" / "v1.8.6-cuda" / "Release" / "whisper-cli.exe"
    )
    assert any(candidate.name == "whisper-cli" for candidate in candidates)


def test_mediacrawler_path_prefers_environment(monkeypatch, tmp_path) -> None:
    configured = tmp_path / "MediaCrawler"
    configured.mkdir()
    (configured / "main.py").write_text("", encoding="utf-8")
    (configured / "pyproject.toml").write_text("", encoding="utf-8")

    monkeypatch.setenv("XHS_MEDIACRAWLER_PATH", str(configured))

    assert mediacrawler_path_candidates()[0] == configured
    assert mediacrawler_path() == configured
