import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from video_bundle_agent.bundle.schema import SourceInfo
from video_bundle_agent.diagnostics.models import DiagnosticLog
from video_bundle_agent.providers.xiaohongshu.provider import (
    _diagnose_xhs_comment_failure,
    _download_media_files,
    _extract_note_id_from_url,
    _fetch_mediacrawler_comments_payload,
    _load_cookie_string,
    analyze_xiaohongshu,
)


def test_extract_xiaohongshu_note_id_from_supported_urls() -> None:
    assert (
        _extract_note_id_from_url("https://www.xiaohongshu.com/explore/abc123?xsec_token=tok")
        == "abc123"
    )
    assert _extract_note_id_from_url("https://www.xiaohongshu.com/discovery/item/def456") == (
        "def456"
    )
    assert (
        _extract_note_id_from_url("https://www.xiaohongshu.com/user/profile/user123/ghi789")
        == "ghi789"
    )
    assert (
        _extract_note_id_from_url(
            "https://www.xiaohongshu.com/login?redirectPath="
            "https%3A%2F%2Fwww.xiaohongshu.com%2Fdiscovery%2Fitem%2Fabc789%3Fxsec_token%3Dtok"
        )
        == "abc789"
    )


def test_load_xiaohongshu_cookie_string_from_netscape_file(tmp_path: Path) -> None:
    cookies = tmp_path / "xiaohongshu.cookies.txt"
    cookies.write_text(
        "\n".join(
            [
                "# Netscape HTTP Cookie File",
                ".xiaohongshu.com\tTRUE\t/\tTRUE\t2147483647\ta1\ta-one",
                ".xiaohongshu.com\tTRUE\t/\tTRUE\t2147483647\tweb_session\tsession",
                ".xiaohongshu.com\tTRUE\t/\tTRUE\t2147483647\twebId\tweb-id",
                ".example.com\tTRUE\t/\tTRUE\t2147483647\tignored\tvalue",
            ]
        ),
        encoding="utf-8",
    )

    cookie_string = _load_cookie_string(cookies)

    assert "a1=a-one" in cookie_string
    assert "web_session=session" in cookie_string
    assert "webId=web-id" in cookie_string
    assert "ignored=value" not in cookie_string


def test_analyze_xiaohongshu_writes_basic_bundle(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    note = {
        "note_id": "abc123",
        "title": "XHS video",
        "desc": "Video description",
        "type": "video",
        "time": 1_700_000_000_000,
        "last_update_time": 1_700_000_010_000,
        "user": {"nickname": "Author", "user_id": "user123"},
        "interact_info": {
            "liked_count": "9",
            "comment_count": "2",
            "collected_count": "3",
            "share_count": "4",
        },
        "tag_list": [{"name": "AI"}],
        "image_list": [{"url_default": "https://sns-img-bd.xhscdn.com/x/y/z!nd"}],
        "video": {
            "media": {
                "stream": {
                    "h264": [
                        {
                            "master_url": "https://sns-video-bd.xhscdn.com/video.mp4",
                            "width": 1920,
                            "height": 1080,
                            "video_bitrate": 1000,
                        }
                    ]
                }
            }
        },
    }

    def fake_fetch_note_data(**kwargs: Any) -> tuple[str, str, str, dict[str, Any], str]:
        return (
            "https://www.xiaohongshu.com/explore/abc123",
            "abc123",
            "<html></html>",
            note,
            "test",
        )

    def fake_download_media_files(**kwargs: Any) -> tuple[Path, list[Path], list]:
        output_dir = kwargs["output_dir"]
        video_path = output_dir / "raw" / "media" / "abc123.mp4"
        image_path = output_dir / "raw" / "media" / "abc123.image-01.png"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"video")
        image_path.write_bytes(b"image")
        return video_path, [video_path, image_path], []

    def fake_fetch_mediacrawler_comments_payload(**kwargs: Any) -> dict[str, Any]:
        return {
            "source": {
                "platform": "xiaohongshu",
                "source_id": "abc123",
                "url": kwargs["source"].source_url,
            },
            "fetched_at": "2026-06-06T00:00:00+00:00",
            "count_fetched": 1,
            "total_reported": None,
            "selection": {
                "sort": "like_count_desc",
                "limit": kwargs["max_comments"],
                "candidate_source": "test",
            },
            "items": [
                {
                    "id": "c1",
                    "parent_id": None,
                    "author_name": "A",
                    "author_id": "u1",
                    "text": "useful",
                    "like_count": 5,
                    "reply_count": 0,
                    "published_at": "",
                    "updated_at": "",
                    "is_top_level": True,
                    "source": "test",
                }
            ],
            "stats": {"top_liked": [], "top_replied": [], "top_terms": []},
        }

    def fake_transcribe_working_video(**kwargs: Any) -> list[dict[str, Any]]:
        segments = [{"id": "0", "start": 0.0, "end": 1.0, "text": "hello", "source": "test"}]
        output_dir = kwargs["output_dir"]
        from video_bundle_agent.providers.xiaohongshu.provider import _write_transcript_artifacts

        _write_transcript_artifacts(
            output_dir=output_dir,
            artifacts=kwargs["artifacts"],
            source=kwargs["source"],
            segments=segments,
            language="zh",
            transcript_source="test",
        )
        return segments

    def fake_create_visual_recall_slides(**kwargs: Any) -> tuple[dict[str, Any], list[Path], list]:
        screenshot = kwargs["output_dir"] / "screenshots" / "candidates" / "000000.0s_fixed.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        screenshot.write_bytes(b"png")
        return (
            {
                "source": kwargs["source"].model_dump(mode="json"),
                "video": {"path": "raw/media/abc123.mp4"},
                "extraction": {"visual_recall": kwargs["visual_recall"]},
                "items": [
                    {
                        "id": "slide_0001",
                        "path": "screenshots/candidates/000000.0s_fixed.png",
                    }
                ],
            },
            [screenshot],
            [],
        )

    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider._fetch_note_data",
        fake_fetch_note_data,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider._download_media_files",
        fake_download_media_files,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider._fetch_mediacrawler_comments_payload",
        fake_fetch_mediacrawler_comments_payload,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider._transcribe_working_video",
        fake_transcribe_working_video,
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider.create_visual_recall_slides",
        fake_create_visual_recall_slides,
    )

    result = analyze_xiaohongshu(
        "https://www.xiaohongshu.com/explore/abc123",
        tmp_path,
        fetch_comments=True,
        max_comments=100,
        visual_recall="high",
        visual_strategy="all",
    )

    bundle = json.loads((tmp_path / "bundle.json").read_text(encoding="utf-8"))
    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    comments = json.loads((tmp_path / "comments.json").read_text(encoding="utf-8"))

    assert result["report_ready"] is True
    assert bundle["source"]["platform"] == "xiaohongshu"
    assert bundle["media_path"] == "media.json"
    assert bundle["working_video_path"] == "raw/media/abc123.mp4"
    assert bundle["capabilities"]["has_transcript"] is True
    assert bundle["capabilities"]["has_slides"] is True
    assert metadata["title"] == "XHS video"
    assert metadata["like_count"] == 9
    assert comments["count_fetched"] == 1


def test_analyze_xiaohongshu_records_comment_cookie_requirement(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    note = {
        "note_id": "abc123",
        "title": "XHS image",
        "desc": "Image description",
        "type": "normal",
        "user": {"nickname": "Author", "user_id": "user123"},
        "interact_info": {"liked_count": "9", "comment_count": "2"},
        "image_list": [{"url_default": "https://sns-img-bd.xhscdn.com/x/y/z!nd"}],
    }

    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider._fetch_note_data",
        lambda **kwargs: (
            "https://www.xiaohongshu.com/explore/abc123",
            "abc123",
            "<html></html>",
            note,
            "test",
        ),
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider._download_media_files",
        lambda **kwargs: (None, [], []),
    )
    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider._fetch_mediacrawler_comments_payload",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError(
                "MediaCrawler did not write detail_comments jsonl output. selfinfo_ok=False"
            )
        ),
    )

    result = analyze_xiaohongshu(
        "https://www.xiaohongshu.com/explore/abc123",
        tmp_path,
        fetch_comments=True,
        visual_recall="none",
    )

    diagnostics = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    codes = [record["code"] for record in diagnostics["records"]]
    assert result["status"] == "warning"
    assert "COOKIE_REQUIRED" in codes
    assert "COMMENTS_UNAVAILABLE" in codes
    assert "TRANSCRIPT_UNAVAILABLE" in codes


def test_fetch_mediacrawler_comments_payload_normalizes_raw_comments(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    mediacrawler_dir = tmp_path / "MediaCrawler"
    mediacrawler_dir.mkdir()
    (mediacrawler_dir / "main.py").write_text("# main\n", encoding="utf-8")
    monkeypatch.setenv("XHS_MEDIACRAWLER_PATH", str(mediacrawler_dir))
    monkeypatch.chdir(tmp_path)

    def fake_run_command(args: list[Any], **kwargs: Any) -> SimpleNamespace:
        raw_dir = Path(args[4])
        assert raw_dir.is_absolute()
        comments_dir = raw_dir / "xhs" / "jsonl"
        comments_dir.mkdir(parents=True, exist_ok=True)
        (comments_dir / "detail_comments_2026-06-11.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "comment_id": "c-low",
                            "content": "low",
                            "like_count": "1",
                            "create_time": 1_700_000_000_000,
                            "nickname": "Low",
                            "user_id": "u-low",
                        }
                    ),
                    json.dumps(
                        {
                            "comment_id": "c-high",
                            "content": "high",
                            "like_count": "9",
                            "create_time": 1_700_000_010_000,
                            "nickname": "High",
                            "user_id": "u-high",
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider.run_command",
        fake_run_command,
    )

    payload = _fetch_mediacrawler_comments_payload(
        source=SourceInfo(
            platform="xiaohongshu",
            source_url="https://www.xiaohongshu.com/explore/abc123",
            resolved_url="https://www.xiaohongshu.com/explore/abc123?xsec_token=tok",
            source_id="abc123",
        ),
        output_dir=Path("relative-bundle"),
        max_comments=1,
    )

    assert payload["count_fetched"] == 1
    assert payload["items"][0]["id"] == "c-high"
    assert payload["items"][0]["source"] == "mediacrawler"
    assert payload["selection"]["candidate_source"] == "mediacrawler_detail_jsonl"


def test_xiaohongshu_comment_account_abnormal_is_permission_required() -> None:
    diagnostics = DiagnosticLog()
    _diagnose_xhs_comment_failure(
        diagnostics,
        RuntimeError("MediaCrawler failed: 300011 当前账号存在异常，请切换账号后重试"),
    )

    payload = diagnostics.model_dump(mode="json")
    record = payload["records"][0]

    assert record["code"] == "PERMISSION_REQUIRED"
    assert record["severity"] == "warning"
    assert record["details"]["xhs_code"] == 300011


def test_download_media_files_keeps_video_when_image_fails(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fake_download_file(**kwargs: Any) -> Path:
        url = kwargs["url"]
        if "image" in url:
            raise RuntimeError("image failed")
        output_path = kwargs["output_path_without_suffix"].with_suffix(".mp4")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"video")
        return output_path

    monkeypatch.setattr(
        "video_bundle_agent.providers.xiaohongshu.provider._download_file",
        fake_download_file,
    )

    working_video, downloaded, warnings = _download_media_files(
        output_dir=tmp_path,
        source_id="abc123",
        media={
            "video_urls": ["https://example.test/video.mp4"],
            "image_urls": ["https://example.test/image.png"],
        },
        cookie_string="",
    )

    assert working_video is not None
    assert downloaded == [working_video]
    assert warnings[0]["code"] == "MEDIA_DOWNLOAD_FAILED"
