from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.context_packer import reorder_for_long_context
from rag.document_index import (
    build_document_summary_index,
    build_document_summary_records,
    load_document_summary_index,
    save_document_summary_index,
    select_document_ids,
)
from rag.evidence_organizer import format_structured_evidence, organize_evidence
from rag.metadata import build_metadata
from rag.retrieval_pipeline import build_retrieval_trace


def _chunk(text: str, metadata: dict) -> dict:
    return {"page_content": text, "metadata": metadata}


def test_reorder_for_long_context_keeps_top_evidence_at_edges():
    plan = {
        "preferred_stores": ["knowledge_db"],
        "metadata_hints": {
            "source_classes": ["domain_reference"],
            "debate_utility": ["mechanism"],
            "topic_family": "international relations",
            "time_scope": "durable",
        },
    }
    chunks = [
        _chunk("weak filler content", {"source_class": "article", "debate_utility": ["example"], "topic_family": "international relations", "time_scope": "recent", "source_quality": "medium"}),
        _chunk("strong mechanism theory about sovereignty and deterrence", {"source_class": "domain_reference", "debate_utility": ["mechanism"], "topic_family": "international relations", "time_scope": "durable", "source_quality": "high"}),
        _chunk("second strong clash analysis on deterrence and sovereignty", {"source_class": "domain_reference", "debate_utility": ["mechanism"], "topic_family": "international relations", "time_scope": "durable", "source_quality": "high"}),
    ]

    reordered = reorder_for_long_context(chunks, "sovereignty deterrence mechanism", plan, "knowledge_db")

    assert reordered[0]["page_content"].startswith("strong mechanism")
    assert reordered[-1]["page_content"].startswith("second strong")


def test_document_summary_records_group_by_document_id():
    meta = build_metadata("topic_pdf", "knowledge_base/pdfs/topic_pdfs/sample.pdf", {"source_path": "knowledge_base/pdfs/topic_pdfs/sample.pdf"})
    chunks_by_store = {
        "knowledge_db": [
            _chunk("First chunk about sovereignty.", meta),
            _chunk("Second chunk about deterrence.", meta),
        ]
    }

    records = build_document_summary_records(chunks_by_store)

    assert len(records) == 1
    assert records[0]["document_id"] == meta["document_id"]
    assert records[0]["chunk_count"] == 2


def test_build_retrieval_trace_keeps_source_and_query_context():
    meta = build_metadata("news", "https://example.com/story", {"url": "https://example.com/story", "title": "Ukraine sovereignty"})
    chunks = {"knowledge_db": [_chunk("Evidence about sovereignty and deterrence.", meta)]}
    plan = {"store_queries": {"knowledge_db": "ukraine sovereignty deterrence"}}

    trace = build_retrieval_trace(chunks, query_plan=plan)

    assert "knowledge_db" in trace
    assert trace["knowledge_db"][0]["source_ref"] == "https://example.com/story"
    assert "ukraine sovereignty deterrence" in trace["knowledge_db"][0]["query"]


def test_document_summary_index_persists_and_loads():
    meta = build_metadata("topic_pdf", "knowledge_base/pdfs/topic_pdfs/sample.pdf", {"source_path": "knowledge_base/pdfs/topic_pdfs/sample.pdf"})
    chunks_by_store = {
        "knowledge_db": [
            _chunk("First chunk about sovereignty.", meta),
            _chunk("Second chunk about deterrence.", meta),
        ]
    }

    index = build_document_summary_index(chunks_by_store)
    output_path = PROJECT_ROOT / "tests" / "_tmp_document_summaries.json"
    try:
        save_document_summary_index(index, output_path)
        loaded = load_document_summary_index(output_path)

        assert "knowledge_db" in loaded
        assert loaded["knowledge_db"][0]["document_id"] == meta["document_id"]
    finally:
        if output_path.exists():
            output_path.unlink()


def test_select_document_ids_prefers_metadata_aligned_records():
    index = {
        "knowledge_db": [
            {
                "document_id": "doc_recent",
                "summary_text": "recent reporting on sanctions and headlines",
                "source_class": "article",
                "topic_family": "international relations",
                "time_scope": "recent",
                "source_quality": "medium",
                "debate_utility": ["example"],
            },
            {
                "document_id": "doc_foundation",
                "summary_text": "sovereignty deterrence security dilemma framework",
                "source_class": "domain_reference",
                "topic_family": "international relations",
                "time_scope": "durable",
                "source_quality": "high",
                "debate_utility": ["mechanism", "definition"],
            },
        ]
    }
    plan = {
        "metadata_hints": {
            "source_classes": ["domain_reference"],
            "debate_utility": ["mechanism"],
            "topic_family": "international relations",
            "time_scope": "durable",
        }
    }

    selected = select_document_ids(index, "knowledge_db", "sovereignty deterrence mechanism", plan=plan, limit=1)

    assert selected == ["doc_foundation"]


def test_organize_evidence_sorts_chunks_by_debate_function():
    definition_meta = build_metadata("wikipedia", "https://example.com/wiki", {"url": "https://example.com/wiki", "title": "Sovereignty"})
    mechanism_meta = build_metadata("debate_theory", "knowledge_base/pdfs/debate.pdf", {"source_path": "knowledge_base/pdfs/debate.pdf"})
    example_meta = build_metadata("news", "https://example.com/news", {"url": "https://example.com/news", "title": "Ukraine case"})

    chunks = {
        "knowledge_db": [
            _chunk("Sovereignty refers to supreme authority within a territory.", definition_meta),
            _chunk("Ukraine creates a live example of sovereignty pressure.", example_meta),
        ],
        "reasoning_db": [
            _chunk("The security dilemma explains why deterrence can produce escalation.", mechanism_meta),
        ],
    }

    organized = organize_evidence(chunks)

    assert organized["definitions"][0]["text"].startswith("Sovereignty refers")
    assert organized["mechanisms"][0]["text"].startswith("The security dilemma")
    assert organized["examples"][0]["text"].startswith("Ukraine creates")


def test_format_structured_evidence_creates_sectioned_block():
    evidence = {
        "definitions": [{"text": "Definition line", "source_ref": "wiki"}],
        "mechanisms": [{"text": "Mechanism line", "source_ref": "theory"}],
    }

    block = format_structured_evidence(evidence, per_section=1)

    assert "DEFINITIONS:" in block
    assert "[source: wiki] Definition line" in block
    assert "MECHANISMS:" in block
