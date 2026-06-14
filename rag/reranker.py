from __future__ import annotations


def chunk_content(chunk) -> tuple[str, dict]:
    if hasattr(chunk, "page_content"):
        return chunk.page_content, getattr(chunk, "metadata", {}) or {}
    return chunk.get("page_content", ""), chunk.get("metadata", {}) or {}


def coerce_utility(metadata: dict) -> list[str]:
    utilities = metadata.get("debate_utility") or []
    if isinstance(utilities, list):
        return [str(item).strip().lower() for item in utilities if str(item).strip()]
    if isinstance(utilities, str):
        return [utilities.strip().lower()] if utilities.strip() else []
    return []


def chunk_score(chunk, query: str, plan: dict | None, store_name: str) -> int:
    content, metadata = chunk_content(chunk)
    score = 0
    lowered_content = content.lower()
    query_terms = [term for term in query.lower().split() if len(term) > 3]

    for term in query_terms[:8]:
        if term in lowered_content:
            score += 2

    if not plan:
        return score

    hints = plan.get("metadata_hints", {}) or {}
    preferred_stores = plan.get("preferred_stores", []) or []
    if store_name in preferred_stores:
        score += 2

    source_class = str(metadata.get("source_class", "")).strip().lower()
    if source_class and source_class in {item.lower() for item in hints.get("source_classes", []) or []}:
        score += 3

    topic_family = str(metadata.get("topic_family", "")).strip().lower()
    hinted_family = str(hints.get("topic_family", "")).strip().lower()
    if topic_family and hinted_family and topic_family == hinted_family:
        score += 2

    time_scope = str(metadata.get("time_scope", "")).strip().lower()
    hinted_scope = str(hints.get("time_scope", "")).strip().lower()
    if time_scope and hinted_scope and time_scope == hinted_scope:
        score += 1

    utilities = set(coerce_utility(metadata))
    desired_utilities = {str(item).strip().lower() for item in hints.get("debate_utility", []) or []}
    score += len(utilities & desired_utilities) * 2

    source_ref = str(
        metadata.get("source_path")
        or metadata.get("url")
        or metadata.get("video_id")
        or ""
    ).strip()
    preferred_sources = {str(item).strip() for item in hints.get("preferred_sources", []) or []}
    weak_sources = {str(item).strip() for item in hints.get("weak_sources", []) or []}
    if source_ref and source_ref in preferred_sources:
        score += 4
    if source_ref and source_ref in weak_sources:
        score -= 3

    quality = str(metadata.get("source_quality", "")).strip().lower()
    if quality == "high":
        score += 2
    elif quality == "medium":
        score += 1

    return score


def rerank_chunks(chunks: list, query: str, plan: dict | None, store_name: str, limit: int) -> list:
    if not chunks:
        return []

    ranked = sorted(
        chunks,
        key=lambda chunk: chunk_score(chunk, query, plan, store_name),
        reverse=True,
    )

    deduped = []
    seen = set()
    for chunk in ranked:
        content, _ = chunk_content(chunk)
        signature = " ".join(content.lower().split())[:220]
        if not signature or signature in seen:
            continue
        seen.add(signature)
        deduped.append(chunk)
        if len(deduped) >= limit:
            break
    return deduped
