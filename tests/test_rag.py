from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.chunking_strategy import get_splitter
from rag.embeddings import EMBEDDING_MAP
from rag.ingest import load_sources, validate_sources
from rag.retrieval_pipeline import RETRIEVAL_CONFIG, format_retrieved_context, retrieve_for_node


def run_rag_smoke_test():
    print("Splitters:")
    for doc_type in ["topic_pdf", "your_speech", "argument_theory", "youtube_debate"]:
        splitter = get_splitter(doc_type)
        print(f"  {doc_type:<16} -> {splitter.__class__.__name__}")

    print("Embeddings:")
    for store_name, embedding in EMBEDDING_MAP.items():
        print(f"  {store_name:<12} -> {embedding.__class__.__name__}")

    print("Retrieval config:")
    for node_name, config in RETRIEVAL_CONFIG.items():
        print(f"  {node_name}: {', '.join(sorted(config.keys()))}")

    sources = load_sources()
    issues = validate_sources(sources)
    print(f"Source validation issues: {len(issues)}")

    chunks = retrieve_for_node("coach_node", "feminism argument")
    print(f"Retrieved chunks in current environment: {len(chunks)}")

    sample_context = format_retrieved_context(
        [
            {
                "page_content": "Sample reasoning chunk",
                "metadata": {"source_path": "knowledge_base/pdfs/topic_pdfs/sample_topic.pdf"},
            }
        ]
    )
    assert "Sample reasoning chunk" in sample_context
    print("Context formatting check passed.")


if __name__ == "__main__":
    run_rag_smoke_test()
