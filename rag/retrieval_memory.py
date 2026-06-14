from __future__ import annotations

from collections import defaultdict
import re

from core.topic_utils import topic_keywords, topic_name
from memory.weekly_store import load_log


def _normalize_terms(text: str) -> list[str]:
    seen: list[str] = []
    for token in re.findall(r"\b[a-zA-Z]{4,24}\b", str(text or "").lower()):
        if token not in seen:
            seen.append(token)
    return seen


def _topic_overlap_score(topic: str, entry_topic: str) -> int:
    current_terms = set(topic_keywords(topic))
    prior_terms = set(topic_keywords(entry_topic))
    if not current_terms or not prior_terms:
        return 0
    return len(current_terms & prior_terms)


def _entry_concept_terms(entry: dict) -> set[str]:
    concepts = entry.get("concepts") or []
    terms: set[str] = set()
    for item in concepts[:4]:
        terms.update(_normalize_terms(item)[:4])
    return terms


def _lesson_quality(entry: dict) -> float:
    retrieval_memory = entry.get("retrieval_memory") or {}
    top_articles = entry.get("top_articles") or []
    key_facts = entry.get("key_facts") or []
    concepts = entry.get("concepts") or []
    vocab_words = entry.get("vocab_words") or []

    score = 0.0
    if retrieval_memory:
        score += 0.35
    score += min(len(top_articles), 2) * 0.08
    score += min(len(key_facts), 2) * 0.08
    score += min(len(concepts), 3) * 0.08
    score += min(len(vocab_words), 3) * 0.04
    return min(round(score, 3), 1.0)


def compact_retrieval_snapshot(state: dict) -> dict:
    snapshot: dict[str, dict] = {}
    plans = state.get("retrieval_plans", {}) or {}
    traces = state.get("retrieval_traces", {}) or {}

    for node_name, plan in plans.items():
        node_trace = traces.get(node_name, {}) or {}
        store_queries = (plan or {}).get("store_queries", {}) or {}
        compact_queries = {
            store_name: " ".join(_normalize_terms(query)[:12])
            for store_name, query in store_queries.items()
            if str(query).strip()
        }
        key_terms: list[str] = []
        source_refs: list[str] = []
        source_scores: dict[str, float] = {}
        for store_items in node_trace.values():
            for item in store_items[:3]:
                for term in _normalize_terms(item.get("preview", ""))[:6]:
                    if term not in key_terms:
                        key_terms.append(term)
                source_ref = str(item.get("source_ref", "")).strip()
                if source_ref and source_ref not in source_refs:
                    source_refs.append(source_ref)
                if source_ref:
                    source_scores[source_ref] = max(
                        source_scores.get(source_ref, 0.0),
                        1.0 if item.get("source_class") in {"debate_theory", "domain_reference"} else 0.6,
                    )
        snapshot[node_name] = {
            "store_queries": compact_queries,
            "key_terms": key_terms[:12],
            "source_refs": source_refs[:4],
            "source_scores": {key: round(value, 3) for key, value in list(source_scores.items())[:4]},
        }
    return snapshot


def recall_retrieval_memory(topic: str, node_name: str, limit_days: int = 14) -> dict:
    log = load_log()
    best_score = -1
    best_memory: dict = {}
    days_seen = 0
    topic_terms = set(topic_keywords(topic))

    for day in sorted(log.keys(), reverse=True):
        for entry in log.get(day, []) or []:
            entry_topic = topic_name(entry.get("topic"))
            score = _topic_overlap_score(topic, entry_topic)
            if topic_terms:
                score += len(topic_terms & _entry_concept_terms(entry))
            score += _lesson_quality(entry)
            if score <= 0:
                continue
            retrieval_memory = (entry.get("retrieval_memory") or {}).get(node_name, {})
            if retrieval_memory and score > best_score:
                best_score = score
                best_memory = retrieval_memory
        days_seen += 1
        if days_seen >= limit_days:
            break

    return best_memory


def source_performance_summary(topic: str, node_name: str, limit_days: int = 21) -> dict:
    log = load_log()
    topic_terms = set(topic_keywords(topic))
    source_totals: dict[str, dict[str, float]] = defaultdict(lambda: {"score": 0.0, "count": 0.0})
    days_seen = 0

    for day in sorted(log.keys(), reverse=True):
        for entry in log.get(day, []) or []:
            entry_topic = topic_name(entry.get("topic"))
            similarity = _topic_overlap_score(topic, entry_topic)
            if topic_terms:
                similarity += len(topic_terms & _entry_concept_terms(entry))
            if similarity <= 0:
                continue

            lesson_quality = _lesson_quality(entry)
            retrieval_memory = (entry.get("retrieval_memory") or {}).get(node_name, {})
            for source_ref in retrieval_memory.get("source_refs", []) or []:
                clean = str(source_ref).strip()
                if not clean:
                    continue
                source_totals[clean]["score"] += lesson_quality
                source_totals[clean]["count"] += 1
            for source_ref, weight in (retrieval_memory.get("source_scores") or {}).items():
                clean = str(source_ref).strip()
                if not clean:
                    continue
                source_totals[clean]["score"] += float(weight) * max(lesson_quality, 0.2)
                source_totals[clean]["count"] += 1
        days_seen += 1
        if days_seen >= limit_days:
            break

    ranked = []
    for source_ref, totals in source_totals.items():
        avg = totals["score"] / totals["count"] if totals["count"] else 0.0
        ranked.append((source_ref, round(avg, 3), int(totals["count"])))
    ranked.sort(key=lambda item: (item[1], item[2]), reverse=True)

    return {
        "preferred_sources": [item[0] for item in ranked[:4] if item[1] >= 0.35],
        "weak_sources": [item[0] for item in ranked if item[1] < 0.2][:4],
        "source_rankings": ranked[:8],
    }
