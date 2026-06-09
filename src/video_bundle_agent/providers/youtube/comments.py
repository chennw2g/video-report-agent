from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any


def _iso_from_timestamp(value: Any) -> str:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, UTC).isoformat()
    return value if isinstance(value, str) else ""


def _text_terms(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    words: Counter[str] = Counter()
    for item in items:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_'-]{2,}", item.get("text", "").lower()):
            words[word] += 1
    return [{"term": term, "count": count} for term, count in words.most_common(20)]


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def normalize_comments(
    *,
    source_id: str,
    url: str,
    raw_comments: list[dict[str, Any]],
    max_comments: int,
) -> dict[str, Any]:
    normalized_items: list[dict[str, Any]] = []
    for raw in raw_comments:
        parent_id = raw.get("parent") or raw.get("parent_id")
        text = raw.get("text") or raw.get("comment") or ""
        item = {
            "id": str(raw.get("id") or ""),
            "parent_id": parent_id,
            "author_name": raw.get("author") or raw.get("author_name") or "",
            "author_id": raw.get("author_id") or raw.get("author_channel_id") or "",
            "text": text,
            "like_count": int(raw.get("like_count") or 0),
            "reply_count": int(raw.get("reply_count") or 0),
            "published_at": _iso_from_timestamp(raw.get("timestamp")),
            "updated_at": _iso_from_timestamp(raw.get("updated_at")),
            "is_top_level": parent_id in (None, "", "root"),
            "source": "yt_dlp",
        }
        normalized_items.append(item)

    items = sorted(
        normalized_items,
        key=lambda item: (item["like_count"], item["reply_count"]),
        reverse=True,
    )[:max_comments]
    top_liked = items[:10]
    top_replied = sorted(items, key=lambda item: item["reply_count"], reverse=True)[:10]
    question_comments = [item for item in items if "?" in item["text"] or "？" in item["text"]][:20]
    critical_terms = ("bad", "wrong", "error", "issue", "problem", "terrible", "差", "错", "问题")
    supportive_terms = ("thanks", "great", "good", "love", "helpful", "谢谢", "赞", "好")
    critical_comments = [item for item in items if _contains_any(item["text"], critical_terms)][:20]
    supportive_comments = [
        item for item in items if _contains_any(item["text"], supportive_terms)
    ][:20]

    return {
        "source": {
            "platform": "youtube",
            "source_id": source_id,
            "url": url,
        },
        "fetched_at": datetime.now(UTC).isoformat(),
        "count_fetched": len(items),
        "total_reported": None,
        "selection": {
            "sort": "like_count_desc",
            "limit": max_comments,
            "candidate_source": "yt_dlp_write_comments",
        },
        "items": items,
        "stats": {
            "top_liked": top_liked,
            "top_replied": top_replied,
            "top_terms": _text_terms(items),
            "question_comments": question_comments,
            "critical_comments": critical_comments,
            "supportive_comments": supportive_comments,
        },
    }
