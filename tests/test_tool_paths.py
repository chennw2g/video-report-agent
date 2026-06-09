from pathlib import Path

from video_bundle_agent.tools.paths import WORKSHOP_ROOT, candidate_paths


def test_workshop_node_is_preferred_before_path_candidates() -> None:
    candidates = candidate_paths("node")

    assert candidates[0] == WORKSHOP_ROOT / "NodeJS" / "node.exe"
    assert Path("WindowsApps") not in candidates[0].parts
