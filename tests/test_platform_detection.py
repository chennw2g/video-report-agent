from video_bundle_agent.providers import detect_platform


def test_detect_platform_from_url() -> None:
    assert detect_platform("https://www.youtube.com/watch?v=abc") == "youtube"
    assert detect_platform("https://youtu.be/abc") == "youtube"
    assert detect_platform("https://www.bilibili.com/video/BV123") == "bilibili"
    assert detect_platform("https://www.xiaohongshu.com/explore/123") == "xiaohongshu"
    assert detect_platform("https://example.com/video/1") == "unsupported"
