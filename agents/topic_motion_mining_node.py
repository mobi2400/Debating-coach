from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.topic_utils import topic_name


CACHE_DIR = Path("cache") / "topic_motions"
TARGET_MOTION_COUNT = 60


def _normalize_slug(topic: str) -> str:
    return "-".join(part for part in topic.lower().split() if part)


def _topic_info_list(topic_info: dict, key: str, limit: int = 8) -> list[str]:
    values = topic_info.get(key, []) if isinstance(topic_info, dict) else []
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()][:limit]


def _seed_terms(topic_info: dict, topic: str) -> tuple[list[str], list[str], list[str]]:
    live_cases = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 5)
    concepts = _topic_info_list(topic_info, "key_concepts_own_these_precisely", 6)
    frameworks = _topic_info_list(topic_info, "essential_theoretical_frameworks", 5)

    concept_terms = []
    for item in concepts + frameworks:
        head = str(item).split("?", 1)[0].split("-", 1)[0].split(":", 1)[0].strip()
        if head and head.lower() not in {term.lower() for term in concept_terms}:
            concept_terms.append(head)

    actor_map = {
        "international relations": ["the UN", "regional blocs", "great powers", "middle powers"],
        "geopolitics": ["great powers", "middle powers", "technology regulators", "states"],
        "economics and finance": ["governments", "central banks", "multilateral lenders", "regulators"],
        "feminism and gender": ["governments", "universities", "courts", "political parties"],
    }
    actors = actor_map.get(topic.lower(), ["governments", "states", "public institutions", "regulators"])
    return live_cases, concept_terms, actors


def _generated_motion_templates(topic: str, topic_info: dict) -> list[str]:
    live_cases, concept_terms, actors = _seed_terms(topic_info, topic)
    recurring = _topic_info_list(topic_info, "recurring_motions_at_wudc_level", 10)
    motions: list[str] = [item for item in recurring if item]

    for case in live_cases:
        case_label = case.split("?", 1)[0].strip() or case
        for actor in actors[:3]:
            motions.extend(
                [
                    f"THBT {actor} should prioritise long-term legitimacy over short-term stability in responding to {case_label}",
                    f"THW evaluate {case_label} primarily through the lens of fairness versus feasibility",
                    f"THBT the best response to {case_label} requires institutional reform rather than symbolic condemnation",
                ]
            )

    for concept in concept_terms[:6]:
        motions.extend(
            [
                f"THBT debates on {topic} should prioritise {concept} over implementation convenience",
                f"THW frame controversies in {topic} through {concept} rather than headline outcomes",
                f"THR the way institutions use {concept} in debates about {topic}",
            ]
        )

    value_pairs = [
        ("fairness", "feasibility"),
        ("rights", "stability"),
        ("legitimacy", "efficiency"),
        ("representation", "expert control"),
        ("structural reform", "incrementalism"),
    ]
    for left, right in value_pairs:
        motions.extend(
            [
                f"THBT, in {topic}, {left} should take priority over {right}",
                f"THW defend {left} rather than {right} as the core lens for {topic} policy",
            ]
        )

    cleaned: list[str] = []
    seen: set[str] = set()
    for motion in motions:
        compact = " ".join(str(motion).split()).strip()
        key = compact.lower()
        if compact and key not in seen:
            seen.add(key)
            cleaned.append(compact)
        if len(cleaned) >= TARGET_MOTION_COUNT:
            break
    return cleaned


def topic_motion_mining_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    topic_info = state.get("topic_info", {}) or {}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{_normalize_slug(topic)}.json"

    motions_cleaned: list[str] = []
    motions_raw: list[str] = []
    source_sites: list[str] = ["topic_info", "generated_templates"]
    fetched_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    if cache_path.exists():
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            motions_cleaned = [str(item).strip() for item in payload.get("motions_cleaned", []) if str(item).strip()]
            motions_raw = [str(item).strip() for item in payload.get("motions_raw", []) if str(item).strip()]
            source_sites = payload.get("source_sites", source_sites)
            fetched_at = payload.get("fetched_at", fetched_at)
        except Exception:
            motions_cleaned = []
            motions_raw = []

    if not motions_cleaned:
        motions_cleaned = _generated_motion_templates(topic, topic_info)
        motions_raw = list(motions_cleaned)
        payload = {
            "topic": topic,
            "motions_raw": motions_raw,
            "motions_cleaned": motions_cleaned,
            "source_sites": source_sites,
            "fetched_at": fetched_at,
            "cache_key": cache_path.stem,
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    state["topic_motion_set"] = {
        "topic": topic,
        "motions_raw": motions_raw,
        "motions_cleaned": motions_cleaned,
        "source_sites": source_sites,
        "cache_key": cache_path.stem,
        "cache_path": str(cache_path),
        "fetched_at": fetched_at,
    }
    return state
