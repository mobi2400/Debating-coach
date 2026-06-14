from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from rag.reranker import chunk_content


def group_chunks_by_document(chunks_by_store: dict[str, list]) -> dict[str, list]:
    grouped: dict[str, list] = defaultdict(list)
    for store_chunks in (chunks_by_store or {}).values():
        for chunk in store_chunks or []:
            _, metadata = chunk_content(chunk)
            document_id = str(metadata.get("document_id", "")).strip()
            if not document_id:
                continue
            grouped[document_id].append(chunk)
    return dict(grouped)


def build_document_summary_records(chunks_by_store: dict[str, list]) -> list[dict]:
    records: list[dict] = []
    for document_id, document_chunks in group_chunks_by_document(chunks_by_store).items():
        first_content, first_metadata = chunk_content(document_chunks[0])
        summary_text = " ".join(
            chunk_content(chunk)[0].strip()
            for chunk in document_chunks[:2]
            if chunk_content(chunk)[0].strip()
        )[:500]
        records.append(
            {
                "document_id": document_id,
                "source_class": first_metadata.get("source_class"),
                "topic_family": first_metadata.get("topic_family"),
                "time_scope": first_metadata.get("time_scope"),
                "source_quality": first_metadata.get("source_quality"),
                "source_ref": first_metadata.get("source_path")
                or first_metadata.get("url")
                or first_metadata.get("video_id")
                or "unknown",
                "summary_text": summary_text or first_content[:500],
                "chunk_count": len(document_chunks),
            }
        )
    return records


def build_document_summary_index(chunks_by_store: dict[str, list]) -> dict[str, list[dict]]:
    return {
        store_name: build_document_summary_records({store_name: store_chunks})
        for store_name, store_chunks in (chunks_by_store or {}).items()
        if store_chunks
    }


def save_document_summary_index(index: dict[str, list[dict]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(index or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_document_summary_index(output_path: Path) -> dict[str, list[dict]]:
    if not output_path.exists():
        return {}
    try:
        return json.loads(output_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _normalize_terms(text: str) -> set[str]:
    return {
        term.strip(".,:;!?()[]{}\"'").lower()
        for term in str(text or "").split()
        if term.strip(".,:;!?()[]{}\"'")
    }


def score_document_record(record: dict, query: str, plan: dict | None = None) -> float:
    query_terms = _normalize_terms(query)
    summary_terms = _normalize_terms(record.get("summary_text", ""))
    overlap = len(query_terms & summary_terms)

    score = float(overlap)
    hints = (plan or {}).get("metadata_hints", {}) or {}

    if record.get("topic_family") and record.get("topic_family") == hints.get("topic_family"):
        score += 2.0
    if record.get("time_scope") and record.get("time_scope") == hints.get("time_scope"):
        score += 1.0

    hinted_source_classes = set(hints.get("source_classes") or [])
    if record.get("source_class") in hinted_source_classes:
        score += 1.5

    hinted_utilities = set(hints.get("debate_utility") or [])
    record_utility = set(record.get("debate_utility") or [])
    if hinted_utilities and record_utility:
        score += min(len(hinted_utilities & record_utility), 2)

    quality_bonus = {"high": 1.25, "medium": 0.5}.get(str(record.get("source_quality") or "").lower(), 0.0)
    score += quality_bonus
    return score


def select_document_ids(
    index: dict[str, list[dict]],
    store_name: str,
    query: str,
    plan: dict | None = None,
    limit: int = 4,
) -> list[str]:
    records = list((index or {}).get(store_name) or [])
    if not records:
        return []

    ranked = sorted(
        records,
        key=lambda record: score_document_record(record, query, plan=plan),
        reverse=True,
    )
    return [
        str(record.get("document_id"))
        for record in ranked[:limit]
        if record.get("document_id")
    ]
