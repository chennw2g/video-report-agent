import json
from pathlib import Path
from typing import Any

from video_bundle_agent.providers.bilibili.provider import (
    _load_bilibili_credential,
    _parse_bilibili_subtitle_segments,
    _select_bilibili_subtitle_track,
    analyze_bilibili,
)


def test_load_bilibili_credential_from_netscape_cookies(tmp_path: Path) -> None:
    cookies = tmp_path / "bilibili.cookies.txt"
    cookies.write_text(
        "\n".join(
            [
                "# Netscape HTTP Cookie File",
                ".bilibili.com\tTRUE\t/\tTRUE\t2147483647\tSESSDATA\tsess",
                ".bilibili.com\tTRUE\t/\tTRUE\t2147483647\tbili_jct\tcsrf",
                ".bilibili.com\tTRUE\t/\tTRUE\t2147483647\tbuvid3\tbuvid-three",
                ".bilibili.com\tTRUE\t/\tTRUE\t2147483647\tbuvid4\tbuvid-four",
                ".bilibili.com\tTRUE\t/\tTRUE\t2147483647\tDedeUserID\t123",
                ".bilibili.com\tTRUE\t/\tTRUE\t2147483647\tac_time_value\trefresh",
                "",
            ]
        ),
        encoding="utf-8",
    )

    credential = _load_bilibili_credential(cookies)

    assert credential is not None
    assert credential.sessdata == "sess"
    assert credential.bili_jct == "csrf"
    assert credential.buvid3 == "buvid-three"
    assert credential.buvid4 == "buvid-four"
    assert credential.dedeuserid == "123"
    assert credential.ac_time_value == "refresh"


def test_select_and_parse_bilibili_subtitle_track() -> None:
    subtitle = {
        "subtitles": [
            {
                "lan": "en",
                "lan_doc": "English",
                "subtitle_url": "//example.test/en.json",
            },
            {
                "lan": "ai-zh",
                "lan_doc": "中文（自动生成）",
                "subtitle_url": "//example.test/zh.json",
            },
        ]
    }

    track = _select_bilibili_subtitle_track(subtitle)
    segments = _parse_bilibili_subtitle_segments(
        {"body": [{"from": 1.2, "to": 3.4, "content": "这里是字幕"}]},
        transcript_source="bilibili_auto_subtitle",
    )

    assert track is not None
    assert track["lan"] == "ai-zh"
    assert segments == [
        {
            "id": "00000",
            "start": 1.2,
            "end": 3.4,
            "text": "这里是字幕",
            "source": "bilibili_auto_subtitle",
        }
    ]


def test_analyze_bilibili_basic_provider_writes_bundle(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fake_dump_single_json(*args: Any, **kwargs: Any) -> dict[str, Any]:
        del args, kwargs
        raise AssertionError("API-first Bilibili success path must not call yt-dlp metadata.")

    def fake_download_working_video(
        url: str,
        output_dir: Path,
        **kwargs: Any,
    ) -> Path:
        del url, output_dir, kwargs
        raise AssertionError("API-first Bilibili success path must not call yt-dlp media.")

    def fake_create_visual_recall_slides(**kwargs: Any) -> tuple[dict[str, Any], list[Path], list]:
        screenshot = kwargs["output_dir"] / "screenshots" / "candidates" / "000001.0s_fixed.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        screenshot.write_bytes(b"fake png")
        return (
            {
                "source": kwargs["source"].model_dump(mode="json"),
                "items": [
                    {
                        "id": "slide_0001",
                        "timestamp": 1.0,
                        "path": "screenshots/candidates/000001.0s_fixed.png",
                    }
                ],
            },
            [screenshot],
            [],
        )

    class FakeVideo:
        pass

    async def fake_fetch_api_video_context(**kwargs: Any) -> tuple[Any, dict[str, Any], list, int]:
        del kwargs
        return (
            FakeVideo(),
            {
                "bvid": "BV123",
                "aid": 123,
                "cid": 456,
                "title": "Bilibili example api",
                "desc": "api description",
                "duration": 30,
                "pubdate": 1_700_000_000,
                "owner": {"mid": 10, "name": "UP"},
                "stat": {"view": 200, "like": 10, "reply": 8, "danmaku": 3},
            },
            [{"cid": 456, "page": 1, "part": "P1"}],
            456,
        )

    async def fake_fetch_api_comments(**kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        assert kwargs["aid"] == 123
        return (
            [
                {
                    "rpid": 1,
                    "root": 0,
                    "parent": 0,
                    "mid": 20,
                    "ctime": 1_700_000_001,
                    "like": 3,
                    "rcount": 1,
                    "member": {"mid": "20", "uname": "viewer"},
                    "content": {"message": "这个观点不错"},
                },
                {
                    "rpid": 2,
                    "root": 0,
                    "parent": 0,
                    "mid": 21,
                    "ctime": 1_700_000_002,
                    "like": 30,
                    "rcount": 0,
                    "member": {"mid": "21", "uname": "hot-viewer"},
                    "content": {"message": "高赞评论"},
                }
            ],
            2,
        )

    async def fake_fetch_api_danmakus(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        del kwargs
        raise AssertionError("Bilibili danmaku must not be fetched by default.")

    async def fake_fetch_api_download_url(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["cid"] == 456
        return {
            "dash": {
                "video": [
                    {
                        "base_url": "https://example.test/video.m4s",
                        "height": 1080,
                        "bandwidth": 1_000_000,
                    }
                ],
                "audio": [
                    {
                        "base_url": "https://example.test/audio.m4s",
                        "bandwidth": 128_000,
                    }
                ],
            }
        }

    async def fake_fetch_api_player_v2(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["bvid"] == "BV123"
        assert kwargs["aid"] == 123
        assert kwargs["cid"] == 456
        return {
            "code": 0,
            "data": {
                "view_points": [
                    {
                        "from": 0,
                        "to": 12,
                        "content": "Opening workflow",
                        "imgUrl": "https://example.test/chapter.jpg",
                    },
                    {"from": 12, "to": 30, "content": "Second workflow"},
                ]
            },
        }

    def fake_download_api_working_media(**kwargs: Any) -> tuple[Path, Path]:
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = output_dir / "BV123.api.mp4"
        audio_path = output_dir / "BV123.audio.m4s"
        video_path.write_bytes(b"fake api video")
        audio_path.write_bytes(b"fake api audio")
        return video_path, audio_path

    def fake_transcribe_existing_audio(
        **kwargs: Any,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        assert kwargs["audio_path"].name == "BV123.audio.m4s"
        return (
            {"language": "zh", "model_path": None},
            [{"start": 1.0, "end": 3.0, "text": "你好，B站。"}],
        )

    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider.dump_single_json",
        fake_dump_single_json,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider.download_working_video",
        fake_download_working_video,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider.create_visual_recall_slides",
        fake_create_visual_recall_slides,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._fetch_api_video_context",
        fake_fetch_api_video_context,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._fetch_api_comments",
        fake_fetch_api_comments,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._fetch_api_danmakus",
        fake_fetch_api_danmakus,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._fetch_api_download_url",
        fake_fetch_api_download_url,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._fetch_api_player_v2",
        fake_fetch_api_player_v2,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._download_api_working_media",
        fake_download_api_working_media,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._transcribe_existing_audio",
        fake_transcribe_existing_audio,
    )

    result = analyze_bilibili(
        "https://www.bilibili.com/video/BV123",
        tmp_path,
        fetch_comments=True,
        visual_recall="low",
        visual_strategy="fixed",
    )

    bundle = json.loads((tmp_path / "bundle.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    comments = json.loads((tmp_path / "comments.json").read_text(encoding="utf-8"))
    source_chapters = json.loads(
        (tmp_path / "source_chapters.json").read_text(encoding="utf-8")
    )

    assert result["report_ready"] is True
    assert bundle["source"]["platform"] == "bilibili"
    assert bundle["metadata_path"] == "metadata.json"
    assert bundle["transcript_path"] == "transcript.segments.json"
    assert bundle["comments_path"] == "comments.json"
    assert bundle["source_chapters_path"] == "source_chapters.json"
    assert bundle["danmaku_path"] is None
    assert bundle["slides_path"] == "slides.json"
    assert bundle["capabilities"]["has_transcript"] is True
    assert bundle["capabilities"]["has_comments"] is True
    assert bundle["capabilities"]["has_danmaku"] is False
    assert bundle["capabilities"]["has_slides"] is True
    assert diagnostics["records"] == []
    assert comments["count_fetched"] == 2
    assert comments["total_reported"] == 2
    assert [item["id"] for item in comments["items"]] == ["2", "1"]
    assert comments["selection"]["sort"] == "like_count_desc"
    assert source_chapters["chapter_source"] == "bilibili_player_v2.view_points"
    assert source_chapters["count"] == 2
    assert source_chapters["items"][0]["title"] == "Opening workflow"
    assert manifest["command"]["provider_stage"] == "bilibili_api_primary"
    assert manifest["command"]["max_danmaku"] == 0


def test_analyze_bilibili_uses_auto_subtitle_and_writes_comparison(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    async def fake_fetch_api_video_context(**kwargs: Any) -> tuple[Any, dict[str, Any], list, int]:
        del kwargs
        return (
            object(),
            {
                "bvid": "BVauto",
                "aid": 321,
                "cid": 654,
                "title": "Bilibili subtitle example",
                "duration": 20,
                "pubdate": 1_700_000_000,
                "owner": {"mid": 10, "name": "UP"},
                "stat": {"view": 20, "like": 2, "reply": 0},
            },
            [{"cid": 654, "page": 1, "part": "P1"}],
            654,
        )

    async def fake_fetch_api_player_v2(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["cid"] == 654
        return {
            "code": 0,
            "data": {
                "subtitle": {
                    "subtitles": [
                        {
                            "lan": "ai-zh",
                            "lan_doc": "中文（自动生成）",
                            "subtitle_url": "//example.test/auto.json",
                        }
                    ]
                },
                "view_points": [],
            },
        }

    async def fake_fetch_api_download_url(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["cid"] == 654
        return {"dash": {"video": [{"base_url": "v", "height": 720}], "audio": [{"base_url": "a"}]}}

    def fake_download_bilibili_subtitle_json(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["track"]["lan"] == "ai-zh"
        return {"body": [{"from": 0.0, "to": 2.0, "content": "平台自动字幕"}]}

    def fake_download_api_working_media(**kwargs: Any) -> tuple[Path, Path]:
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = output_dir / "BVauto.api.mp4"
        audio_path = output_dir / "BVauto.audio.m4s"
        video_path.write_bytes(b"fake api video")
        audio_path.write_bytes(b"fake api audio")
        return video_path, audio_path

    def fake_transcribe_existing_audio(
        **kwargs: Any,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        assert kwargs["audio_path"].name == "BVauto.audio.m4s"
        return (
            {"language": "zh", "transcript_source": "funasr_paraformer_zh", "model_path": None},
            [{"start": 0.0, "end": 2.0, "text": "本地转录字幕"}],
        )

    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._fetch_api_video_context",
        fake_fetch_api_video_context,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._fetch_api_player_v2",
        fake_fetch_api_player_v2,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._fetch_api_download_url",
        fake_fetch_api_download_url,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._download_bilibili_subtitle_json",
        fake_download_bilibili_subtitle_json,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._download_api_working_media",
        fake_download_api_working_media,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.bilibili.provider._transcribe_existing_audio",
        fake_transcribe_existing_audio,
    )

    result = analyze_bilibili(
        "https://www.bilibili.com/video/BVauto",
        tmp_path,
        visual_recall="none",
    )

    bundle = json.loads((tmp_path / "bundle.json").read_text(encoding="utf-8"))
    transcript = json.loads((tmp_path / "transcript.segments.json").read_text(encoding="utf-8"))
    alternatives = json.loads(
        (tmp_path / "transcript.alternatives.json").read_text(encoding="utf-8")
    )
    comparison = json.loads((tmp_path / "transcript.comparison.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))

    assert result["capabilities"]["has_transcript"] is True
    assert bundle["transcript_path"] == "transcript.segments.json"
    assert bundle["transcript_alternatives_path"] == "transcript.alternatives.json"
    assert bundle["transcript_comparison_path"] == "transcript.comparison.json"
    assert transcript["transcript_source"] == "bilibili_auto_subtitle"
    assert transcript["segments"][0]["text"] == "平台自动字幕"
    assert alternatives["items"][0]["reason"] == "auto_subtitle_comparison"
    assert comparison["comparison"]["window_count"] >= 1
    assert any(record["code"] == "AUTO_SUBTITLE_COMPARISON" for record in diagnostics["records"])
