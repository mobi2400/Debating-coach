from __future__ import annotations

from collections import defaultdict

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
