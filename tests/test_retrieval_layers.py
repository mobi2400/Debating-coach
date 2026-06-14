from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.context_packer import reorder_for_long_context
from rag.document_index import build_document_summary_records
from rag.metadata import build_metadata


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
