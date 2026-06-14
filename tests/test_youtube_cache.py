from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.youtube_cache import (
    classify_channel_inventory,
    load_channel_cache,
    mark_transcript_status,
    merge_channel_inventory,
    parse_channel_inventory,
    save_channel_cache,
    score_video_relevance,
)


def test_parse_channel_inventory_extracts_video_metadata():
    html = """
    {"videoId":"abc123def45","title":{"runs":[{"text":"How to rebut better"}]},
     "descriptionSnippet":{"runs":[{"text":"Workshop on weighing and burden"}]},
     "publishedTimeText":{"simpleText":"2 days ago"},
     "url":"https://i.ytimg.com/vi/abc123def45/hqdefault.jpg"}
    """

    videos = parse_channel_inventory(html, "https://www.youtube.com/@structural.reasons", limit=5)

    assert len(videos) == 1
    assert videos[0]["video_id"] == "abc123def45"
    assert videos[0]["video_title"] == "How to rebut better"
    assert "weighing and burden" in videos[0]["description_snippet"]


def test_merge_channel_inventory_only_flags_unseen_videos():
    existing = {
        "channel_url": "https://www.youtube.com/@structural.reasons",
        "scan_policy_version": 1,
        "last_scan": None,
        "videos": [
            {"video_id": "abc123def45", "video_title": "Existing title", "transcript_fetched": True}
        ],
    }
    discovered = [
        {"video_id": "abc123def45", "video_title": "Updated title"},
        {"video_id": "zzz999yyy88", "video_title": "New video"},
    ]

    merged, new_items = merge_channel_inventory(existing, discovered)

    assert len(merged["videos"]) == 2
    assert new_items == [{"video_id": "zzz999yyy88", "video_title": "New video"}]


def test_mark_transcript_status_updates_cached_video():
    channel_url = "https://www.youtube.com/@structural.reasons"
    payload = {
        "channel_url": channel_url,
        "scan_policy_version": 1,
        "last_scan": None,
        "videos": [
            {"video_id": "abc123def45", "video_title": "Sample", "transcript_fetched": False, "selection_status": "unclassified"}
        ],
    }
    cache_root = PROJECT_ROOT / "tests" / "_tmp_youtube_cache"
    try:
        save_channel_cache(cache_root, channel_url, payload)

        mark_transcript_status(cache_root, channel_url, "abc123def45", fetched=True)
        updated = load_channel_cache(cache_root, channel_url)

        assert updated["videos"][0]["transcript_fetched"] is True
        assert updated["videos"][0]["selection_status"] == "transcript_fetched"
    finally:
        cache_file = cache_root / "structural-reasons.json"
        if cache_file.exists():
            cache_file.unlink()
        if cache_root.exists():
            cache_root.rmdir()


def test_score_video_relevance_prefers_argument_training_video():
    video = {
        "video_id": "abc123def45",
        "video_title": "How to rebut better in BP debate",
        "description_snippet": "Workshop on weighing, burden, clash and extension strategy.",
    }

    scored = score_video_relevance(video, "youtube_debate")

    assert scored["selection_status"] == "selected"
    assert scored["relevance_score"] >= 3.0
    assert "rebuttal" in scored["argument_skills"] or "weighing" in scored["argument_skills"]


def test_classify_channel_inventory_skips_low_signal_video():
    videos = [
        {
            "video_id": "zzz999yyy88",
            "video_title": "Event announcement and registration details",
            "description_snippet": "Join our livestream and register today.",
        }
    ]

    classified = classify_channel_inventory(videos, "youtube_debate")

    assert classified[0]["selection_status"] == "skipped"


def test_thumbnail_text_can_raise_relevance_score():
    video = {
        "video_id": "abc123def45",
        "video_title": "Round 5",
        "description_snippet": "Practice session.",
        "thumbnail_text": "HOW TO REBUT BETTER",
    }

    scored = score_video_relevance(video, "youtube_debate")

    assert scored["selection_status"] == "selected"
    assert scored["relevance_score"] >= 3.0


def test_classify_channel_inventory_uses_ocr_when_thumbnail_text_missing(monkeypatch):
    monkeypatch.setattr(
        "rag.youtube_cache.extract_thumbnail_text",
        lambda url: "HOW TO WEIGH BETTER",
    )
    videos = [
        {
            "video_id": "ocr123def45",
            "video_title": "Round 6",
            "description_snippet": "Practice session.",
            "thumbnail_url": "https://i.ytimg.com/vi/ocr123def45/hqdefault.jpg",
            "thumbnail_text": "",
        }
    ]

    classified = classify_channel_inventory(videos, "youtube_debate")

    assert classified[0]["thumbnail_text"] == "HOW TO WEIGH BETTER"
    assert classified[0]["selection_status"] == "selected"
