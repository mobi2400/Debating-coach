from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from core.topic_utils import TOPIC_KEYWORDS
from rag.thumbnail_ocr import extract_thumbnail_text

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def channel_slug(channel_url: str) -> str:
    parsed = urlparse(str(channel_url or "").strip())
    raw = (parsed.path or "").strip("/").replace("/", "_") or "channel"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-").lower()
    return slug or "channel"


def cache_path(cache_root: Path, channel_url: str) -> Path:
    return cache_root / f"{channel_slug(channel_url)}.json"


def load_channel_cache(cache_root: Path, channel_url: str) -> dict:
    path = cache_path(cache_root, channel_url)
    if not path.exists():
        return {
            "channel_url": channel_url,
            "scan_policy_version": 1,
            "last_scan": None,
            "videos": [],
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "channel_url": channel_url,
            "scan_policy_version": 1,
            "last_scan": None,
            "videos": [],
        }


def save_channel_cache(cache_root: Path, channel_url: str, payload: dict) -> None:
    path = cache_path(cache_root, channel_url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_channel_inventory(html: str, channel_url: str, limit: int = 25) -> list[dict]:
    seen: dict[str, dict] = {}
    html = str(html or "")
    for match in re.finditer(r'"videoId":"([A-Za-z0-9_-]{11})"', html):
        video_id = match.group(1)
        if video_id in seen:
            continue
        anchor = match.start()
        window = html[max(0, anchor - 800): anchor + 2200]

        title_match = re.search(r'"title":\{"runs":\[\{"text":"([^"]+)"\}\]\}', window)
        if not title_match:
            title_match = re.search(r'"title":"([^"]+)"', window)

        description_match = re.search(r'"descriptionSnippet":\{"runs":\[\{"text":"([^"]+)"\}\]\}', window)
        if not description_match:
            description_match = re.search(r'"description":"([^"]+)"', window)

        thumbnail_match = re.search(r'"url":"(https://i\.ytimg\.com/[^"]+)"', window)
        published_match = re.search(r'"publishedTimeText":\{"simpleText":"([^"]+)"\}', window)

        seen[video_id] = {
            "video_id": video_id,
            "video_title": (title_match.group(1) if title_match else "").replace("\\u0026", "&"),
            "description_snippet": (description_match.group(1) if description_match else "").replace("\\u0026", "&"),
            "thumbnail_url": thumbnail_match.group(1).replace("\\u0026", "&") if thumbnail_match else "",
            "thumbnail_text": "",
            "published_at": published_match.group(1) if published_match else "",
            "channel_url": channel_url,
            "scan_timestamp": _now_iso(),
            "selection_status": "unclassified",
            "selection_reason": "",
            "topic_tags": [],
            "argument_skills": [],
            "relevance_score": 0.0,
            "transcript_fetched": False,
        }
        if len(seen) >= limit:
            break
    return list(seen.values())


def merge_channel_inventory(existing: dict, discovered: list[dict]) -> tuple[dict, list[dict]]:
    existing_videos = {str(item.get("video_id")): dict(item) for item in (existing.get("videos") or [])}
    new_items: list[dict] = []

    for item in discovered:
        video_id = str(item.get("video_id") or "").strip()
        if not video_id:
            continue
        if video_id in existing_videos:
            preserved = existing_videos[video_id]
            preserved.update(
                {
                    "video_title": item.get("video_title", preserved.get("video_title", "")),
                    "description_snippet": item.get("description_snippet", preserved.get("description_snippet", "")),
                    "thumbnail_url": item.get("thumbnail_url", preserved.get("thumbnail_url", "")),
                    "thumbnail_text": item.get("thumbnail_text", preserved.get("thumbnail_text", "")),
                    "published_at": item.get("published_at", preserved.get("published_at", "")),
                    "scan_timestamp": item.get("scan_timestamp", preserved.get("scan_timestamp")),
                }
            )
            existing_videos[video_id] = preserved
        else:
            existing_videos[video_id] = item
            new_items.append(item)

    merged = dict(existing)
    merged["last_scan"] = _now_iso()
    merged["videos"] = list(existing_videos.values())
    return merged, new_items


def mark_transcript_status(cache_root: Path, channel_url: str, video_id: str, fetched: bool) -> None:
    payload = load_channel_cache(cache_root, channel_url)
    videos = []
    for item in payload.get("videos", []) or []:
        if str(item.get("video_id")) == str(video_id):
            updated = dict(item)
            updated["transcript_fetched"] = bool(fetched)
            updated["selection_status"] = "transcript_fetched" if fetched else updated.get("selection_status", "unclassified")
            videos.append(updated)
        else:
            videos.append(item)
    payload["videos"] = videos
    payload["last_scan"] = _now_iso()
    save_channel_cache(cache_root, channel_url, payload)


DEBATE_SIGNAL_TERMS = {
    "argument": 2.0,
    "arguments": 2.0,
    "rebut": 2.0,
    "rebuttal": 2.5,
    "rebuttals": 2.5,
    "weigh": 2.0,
    "weighing": 2.5,
    "framing": 2.0,
    "clash": 2.0,
    "burden": 2.0,
    "extension": 2.0,
    "motion": 2.0,
    "adjudication": 2.0,
    "adjudicator": 2.0,
    "debate": 2.0,
    "debating": 2.0,
    "bp": 1.5,
    "british parliamentary": 2.5,
    "public forum": 1.5,
    "wsdc": 1.5,
    "wudc": 1.5,
    "speaker": 1.0,
    "round": 1.0,
    "case": 1.0,
    "prep": 1.0,
    "strategy": 1.5,
    "analysis": 1.0,
}

NEGATIVE_SIGNAL_TERMS = {
    "trailer": 2.0,
    "shorts": 1.5,
    "livestream": 1.0,
    "announcement": 2.0,
    "registration": 2.5,
    "promo": 2.0,
    "highlights": 1.0,
}

ARGUMENT_SKILL_TERMS = {
    "rebut": "rebuttal",
    "rebuttal": "rebuttal",
    "weigh": "weighing",
    "weighing": "weighing",
    "framing": "framing",
    "clash": "clash",
    "burden": "burden",
    "extension": "extension",
    "mechanism": "mechanism",
    "comparative": "comparative analysis",
}


def _topic_tags(text: str) -> list[str]:
    haystack = str(text or "").lower()
    tags: list[str] = []
    for family, keywords in TOPIC_KEYWORDS.items():
        family_terms = [family] + list(keywords)
        if any(term.lower() in haystack for term in family_terms):
            tags.append(family)
    return tags[:3]


def _argument_skills(text: str) -> list[str]:
    haystack = str(text or "").lower()
    skills: list[str] = []
    for term, label in ARGUMENT_SKILL_TERMS.items():
        if term in haystack and label not in skills:
            skills.append(label)
    return skills[:4]


def score_video_relevance(video: dict, channel_type: str) -> dict:
    title = str(video.get("video_title", "")).strip()
    description = str(video.get("description_snippet", "")).strip()
    thumbnail_text = str(video.get("thumbnail_text", "")).strip()
    corpus = f"{title} {description} {thumbnail_text}".lower()

    score = 0.0
    reasons: list[str] = []
    for term, weight in DEBATE_SIGNAL_TERMS.items():
        if term in corpus:
            score += weight
            reasons.append(f"+{weight:g} {term}")
    for term, weight in NEGATIVE_SIGNAL_TERMS.items():
        if term in corpus:
            score -= weight
            reasons.append(f"-{weight:g} {term}")

    if channel_type == "youtube_debate":
        score += 1.0
        reasons.append("+1 debate channel")
    elif channel_type == "youtube_ted":
        score += 0.5
        reasons.append("+0.5 speech channel")

    topic_tags = _topic_tags(corpus)
    argument_skills = _argument_skills(corpus)
    if topic_tags:
        score += 0.5 * len(topic_tags)
        reasons.append(f"+{0.5 * len(topic_tags):g} topic tags")
    if argument_skills:
        score += 0.5 * len(argument_skills)
        reasons.append(f"+{0.5 * len(argument_skills):g} argument skills")

    selection_status = "selected" if score >= 3.0 else "skipped"
    selection_reason = ", ".join(reasons[:6]) or "no strong debate signals"

    enriched = dict(video)
    enriched["topic_tags"] = topic_tags
    enriched["argument_skills"] = argument_skills
    enriched["relevance_score"] = round(score, 3)
    enriched["selection_status"] = selection_status
    enriched["selection_reason"] = selection_reason
    return enriched


def classify_channel_inventory(videos: list[dict], channel_type: str) -> list[dict]:
    classified = []
    for video in videos or []:
        enriched = dict(video)
        if not str(enriched.get("thumbnail_text", "")).strip():
            enriched["thumbnail_text"] = extract_thumbnail_text(enriched.get("thumbnail_url", ""))
        classified.append(score_video_relevance(enriched, channel_type))
    return classified
