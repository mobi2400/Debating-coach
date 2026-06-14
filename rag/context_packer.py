from __future__ import annotations

from rag.reranker import chunk_content, chunk_score


def reorder_for_long_context(chunks: list, query: str, plan: dict | None, store_name: str) -> list:
    if len(chunks) <= 2:
        return list(chunks)

    scored = [
        (chunk_score(chunk, query, plan, store_name), index, chunk)
        for index, chunk in enumerate(chunks)
    ]
    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)

    best = scored[0][2]
    second_best = scored[1][2] if len(scored) > 1 else None
    middle = [item[2] for item in scored[2:]]
    reordered = [best]
    reordered.extend(middle)
    if second_best is not None:
        reordered.append(second_best)
    return reordered


def format_lane(label: str, chunks: list, query: str = "", plan: dict | None = None, store_name: str = "") -> str:
    if not chunks:
        return ""

    ordered = reorder_for_long_context(chunks, query, plan, store_name)
    lines = [f"{label}:"]
    for chunk in ordered:
        content, metadata = chunk_content(chunk)
        source = (
            metadata.get("source_path")
            or metadata.get("url")
            or metadata.get("video_id")
            or metadata.get("document_id")
            or "unknown"
        )
        lines.append(f"[source: {source}]\n{content}")
    return "\n---\n".join(lines)


def pack_retrieved_context(chunks, labels: dict[str, str] | None = None, query_plan: dict | None = None) -> str:
    labels = labels or {}

    if isinstance(chunks, dict):
        sections = []
        queries = (query_plan or {}).get("store_queries", {}) or {}
        for store_name, store_chunks in chunks.items():
            label = labels.get(store_name, store_name.upper())
            block = format_lane(
                label,
                store_chunks,
                query=queries.get(store_name, ""),
                plan=query_plan,
                store_name=store_name,
            )
            if block:
                sections.append(block)
        return "\n\n".join(sections).strip()

    return format_lane("RETRIEVED CONTEXT", list(chunks)).strip()
