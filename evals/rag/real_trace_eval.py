from __future__ import annotations

from collections import Counter

from memory.weekly_store import load_log


def _safe_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _score_entry(entry: dict) -> dict:
    retrieval_memory = entry.get("retrieval_memory") or {}
    vocab_words = _safe_list(entry.get("vocab_words"))
    concepts = _safe_list(entry.get("concepts"))
    key_facts = _safe_list(entry.get("key_facts"))
    top_articles = _safe_list(entry.get("top_articles"))

    memory_nodes = list(retrieval_memory.keys())
    memory_present = 1.0 if retrieval_memory else 0.0

    unique_sources = set()
    unique_terms = set()
    repeated_sources: list[str] = []
    for node_memory in retrieval_memory.values():
        node_sources = _safe_list((node_memory or {}).get("source_refs"))
        node_terms = _safe_list((node_memory or {}).get("key_terms"))
        for source in node_sources:
            if source in unique_sources and source not in repeated_sources:
                repeated_sources.append(source)
            unique_sources.add(source)
        unique_terms.update(node_terms)

    source_diversity_score = min(len(unique_sources) / 4, 1.0)
    term_coverage_score = min(len(unique_terms) / 8, 1.0)
    concept_score = min(len(concepts) / 3, 1.0)
    fact_score = min(len(key_facts) / 2, 1.0)
    vocab_score = min(len(set(word.lower() for word in vocab_words)) / 3, 1.0)
    article_score = min(len(top_articles) / 2, 1.0)
    duplicate_penalty = 0.15 * len(repeated_sources)

    total = (
        0.25 * memory_present
        + 0.20 * source_diversity_score
        + 0.15 * term_coverage_score
        + 0.15 * concept_score
        + 0.10 * fact_score
        + 0.10 * vocab_score
        + 0.05 * article_score
        - duplicate_penalty
    )
    total = max(0.0, min(round(total, 3), 1.0))

    return {
        "topic": str(entry.get("topic", "")).strip(),
        "memory_nodes": memory_nodes,
        "memory_present": round(memory_present, 3),
        "source_diversity_score": round(source_diversity_score, 3),
        "term_coverage_score": round(term_coverage_score, 3),
        "concept_score": round(concept_score, 3),
        "fact_score": round(fact_score, 3),
        "vocab_score": round(vocab_score, 3),
        "article_score": round(article_score, 3),
        "duplicate_penalty": round(duplicate_penalty, 3),
        "repeated_sources": repeated_sources,
        "total_score": total,
    }


def evaluate_recent_traces(limit_days: int = 7) -> dict:
    log = load_log()
    day_keys = sorted(log.keys(), reverse=True)[:limit_days]
    lesson_scores: list[dict] = []
    node_counter: Counter[str] = Counter()
    low_scoring_topics: list[str] = []
    repeated_sources: Counter[str] = Counter()
    score_bands: Counter[str] = Counter()

    for day in day_keys:
        for entry in log.get(day, []) or []:
            score = _score_entry(entry)
            lesson_scores.append({"date": day, **score})
            for node in score["memory_nodes"]:
                node_counter[node] += 1
            for source in score["repeated_sources"]:
                repeated_sources[source] += 1
            if score["total_score"] < 0.45:
                low_scoring_topics.append(score["topic"])
            if score["total_score"] >= 0.75:
                score_bands["strong"] += 1
            elif score["total_score"] >= 0.45:
                score_bands["mixed"] += 1
            else:
                score_bands["weak"] += 1

    average = round(
        sum(item["total_score"] for item in lesson_scores) / len(lesson_scores),
        3,
    ) if lesson_scores else 0.0

    return {
        "days_scanned": len(day_keys),
        "lessons_scored": len(lesson_scores),
        "average_score": average,
        "node_coverage": dict(node_counter),
        "score_bands": dict(score_bands),
        "low_scoring_topics": low_scoring_topics[:10],
        "repeated_sources": repeated_sources.most_common(5),
        "lesson_scores": lesson_scores,
    }
