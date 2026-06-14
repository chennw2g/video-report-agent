import json
from pathlib import Path

from video_bundle_agent.bundle.schema import SourceInfo
from video_bundle_agent.providers.url_resolution import normalize_youtube_url
from video_bundle_agent.providers.youtube.comments import normalize_comments
from video_bundle_agent.providers.youtube.provider import normalize_source_chapters
from video_bundle_agent.providers.youtube.transcript import parse_json3, parse_vtt


def test_normalize_comments_limits_items_and_builds_stats() -> None:
    payload = normalize_comments(
        source_id="abc",
        url="https://www.youtube.com/watch?v=abc",
        max_comments=2,
        raw_comments=[
            {"id": "1", "author": "A", "text": "Great explanation?", "like_count": 5},
            {"id": "2", "author": "B", "text": "This has a problem", "like_count": 1},
            {"id": "3", "author": "C", "text": "Extra", "like_count": 10},
        ],
    )

    assert payload["count_fetched"] == 2
    assert len(payload["items"]) == 2
    assert [item["id"] for item in payload["items"]] == ["3", "1"]
    assert payload["selection"]["sort"] == "like_count_desc"
    assert payload["stats"]["question_comments"][0]["id"] == "1"
    assert payload["stats"]["critical_comments"] == []


def test_normalize_source_chapters_preserves_zero_start() -> None:
    source = SourceInfo(
        platform="youtube",
        source_url="https://www.youtube.com/watch?v=abc",
        source_id="abc",
    )

    payload = normalize_source_chapters(
        source=source,
        chapters=[
            {"start_time": 0, "end_time": 42.5, "title": "Intro"},
            {"start_time": 42.5, "end_time": 90, "title": "Main point"},
        ],
    )

    assert payload["chapter_source"] == "yt_dlp.chapters"
    assert payload["count"] == 2
    assert payload["items"][0]["title"] == "Intro"
    assert payload["items"][0]["time"] == "00:00-00:42"


def test_parse_json3_transcript(tmp_path: Path) -> None:
    path = tmp_path / "sub.json3"
    path.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "tStartMs": 1000,
                        "dDurationMs": 2000,
                        "segs": [{"utf8": "Hello "}, {"utf8": "world"}],
                    },
                    {"tStartMs": 3000, "dDurationMs": 1000, "segs": [{"utf8": "\n"}]},
                ]
            }
        ),
        encoding="utf-8",
    )

    segments = parse_json3(path)

    assert segments == [
        {
            "id": "0",
            "start": 1.0,
            "end": 3.0,
            "duration": 2.0,
            "text": "Hello world",
            "source": "yt_dlp_subtitle",
        }
    ]


def test_parse_vtt_transcript(tmp_path: Path) -> None:
    path = tmp_path / "sub.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello <b>world</b>\n",
        encoding="utf-8",
    )

    segments = parse_vtt(path)

    assert segments[0]["start"] == 1.0
    assert segments[0]["end"] == 3.0
    assert segments[0]["text"] == "Hello world"


def test_normalize_youtube_short_forms_to_watch_url() -> None:
    assert (
        normalize_youtube_url("https://youtu.be/AOEr5FrW-lY?si=tracking").working_url
        == "https://www.youtube.com/watch?v=AOEr5FrW-lY"
    )
    assert (
        normalize_youtube_url("https://www.youtube.com/shorts/wvzJHVmvEwU?si=x").working_url
        == "https://www.youtube.com/watch?v=wvzJHVmvEwU"
    )
