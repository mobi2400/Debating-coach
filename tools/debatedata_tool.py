from __future__ import annotations

import html
import re
from typing import Iterable

import requests


BASE_URL = "https://debatedata.io/"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DebateCoachBot/1.0)",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}
MOTION_PATTERNS = (
    r"\bTH(?:BT|W|R|S)\b[^\n\r\"<>]{20,260}",
    r"This House[^\n\r\"<>]{20,260}",
)


def _topic_terms(topic: str) -> list[str]:
    topic = " ".join(str(topic).lower().split())
    aliases = {
        "feminism and gender": ["feminism", "gender", "women", "patriarchy", "intersectionality"],
        "international relations": ["international", "relations", "sovereignty", "war", "security"],
        "geopolitics": ["geopolitics", "geopolitical", "china", "russia", "power"],
        "economics and finance": ["economics", "finance", "trade", "inflation", "markets"],
    }
    return aliases.get(topic, [part for part in topic.split() if part])


def _candidate_urls(topic: str) -> list[tuple[str, dict]]:
    base_params = {"dateFrom": 1981, "dateTo": 2026}
    queries = [topic] + _topic_terms(topic)
    params_list: list[tuple[str, dict]] = [(BASE_URL, base_params)]
    for query in queries[:5]:
        for key in ("search", "query", "q", "topic", "tag"):
            params = dict(base_params)
            params[key] = query
            params_list.append((BASE_URL, params))
    return params_list


def _extract_from_text(text: str) -> list[str]:
    decoded = html.unescape(text)
    found: list[str] = []
    seen: set[str] = set()
    for pattern in MOTION_PATTERNS:
        for match in re.findall(pattern, decoded, flags=re.I):
            cleaned = " ".join(str(match).split()).strip(" ,;:-")
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                found.append(cleaned)
    return found


def _extract_json_strings(text: str) -> Iterable[str]:
    for raw in re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', text):
        value = bytes(raw, "utf-8").decode("unicode_escape", errors="ignore")
        if "TH" in value or "This House" in value:
            yield value


def _score_motion(motion: str, topic_terms: list[str]) -> tuple[int, int]:
    lowered = motion.lower()
    score = sum(1 for term in topic_terms if term and term in lowered)
    return score, -len(lowered)


def fetch_debatedata_motions(topic: str, limit: int = 60, timeout: int = 20) -> list[dict]:
    topic_terms = _topic_terms(topic)
    collected: list[dict] = []
    seen: set[str] = set()

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    for url, params in _candidate_urls(topic):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
        except Exception:
            continue

        text = response.text
        motions = _extract_from_text(text)
        if not motions:
            motions = _extract_from_text("\n".join(_extract_json_strings(text)))

        for motion in motions:
            key = motion.lower()
            if key in seen:
                continue
            seen.add(key)
            collected.append(
                {
                    "motion": motion,
                    "source": "debatedata",
                    "url": str(response.url),
                }
            )

        if len(collected) >= limit:
            break

    collected.sort(key=lambda item: _score_motion(item["motion"], topic_terms), reverse=True)
    return collected[:limit]
