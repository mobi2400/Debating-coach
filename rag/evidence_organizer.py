from __future__ import annotations

from rag.reranker import chunk_content


SECTION_ORDER = ["definitions", "mechanisms", "examples", "rebuttals", "style", "general"]


def _section_for_chunk(metadata: dict) -> str:
    utility = {str(item).strip().lower() for item in (metadata.get("debate_utility") or [])}
    source_class = str(metadata.get("source_class") or "").strip().lower()

    if {"definition", "preknowledge", "history"} & utility:
        return "definitions"
    if {"case_evidence", "example"} & utility and source_class in {
        "article",
        "encyclopedic_background",
        "debate_transcript",
        "speech_transcript",
    }:
        return "examples"
    if {"mechanism", "clash"} & utility:
        return "mechanisms"
    if {"case_evidence", "example"} & utility:
        return "examples"
    if "rebuttal" in utility:
        return "rebuttals"
    if "style" in utility or source_class in {"personal_style", "debate_style"}:
        return "style"
    return "general"


def organize_evidence(chunks_by_store: dict[str, list]) -> dict[str, list[dict]]:
    organized = {key: [] for key in SECTION_ORDER}

    for store_name, store_chunks in (chunks_by_store or {}).items():
        for chunk in store_chunks or []:
            content, metadata = chunk_content(chunk)
            section = _section_for_chunk(metadata)
            organized[section].append(
                {
                    "text": " ".join(content.split()).strip(),
                    "source_ref": metadata.get("source_path")
                    or metadata.get("url")
                    or metadata.get("video_id")
                    or "unknown",
                    "store": store_name,
                    "metadata": metadata,
                }
            )

    return {section: items for section, items in organized.items() if items}


def format_structured_evidence(evidence: dict[str, list[dict]], per_section: int = 2) -> str:
    blocks: list[str] = []
    for section in SECTION_ORDER:
        items = list((evidence or {}).get(section) or [])[:per_section]
        if not items:
            continue
        lines = [section.upper() + ":"]
        for item in items:
            lines.append(f"[source: {item['source_ref']}] {item['text']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks).strip()
