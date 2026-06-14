from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.query_planner import build_query_plan
from rag.retrieval_memory import compact_retrieval_snapshot, recall_retrieval_memory, source_performance_summary
from rag.reranker import chunk_score


def test_compact_retrieval_snapshot_keeps_queries_terms_and_sources():
    state = {
        "retrieval_plans": {
            "argue_node": {
                "store_queries": {
                    "knowledge_db": "international relations sovereignty precedent impact",
                    "reasoning_db": "burden clash rebuttal mechanism",
                }
            }
        },
        "retrieval_traces": {
            "argue_node": {
                "knowledge_db": [
                    {
                        "source_ref": "https://example.com/article",
                        "preview": "Sovereignty and precedent matter when institutions enforce norms selectively.",
                    }
                ]
            }
        },
    }

    snapshot = compact_retrieval_snapshot(state)

    assert "argue_node" in snapshot
    assert "knowledge_db" in snapshot["argue_node"]["store_queries"]
    assert "sovereignty" in snapshot["argue_node"]["key_terms"]
    assert snapshot["argue_node"]["source_refs"] == ["https://example.com/article"]


def test_recall_retrieval_memory_prefers_overlapping_topic(monkeypatch):
    monkeypatch.setattr(
        "rag.retrieval_memory.load_log",
        lambda: {
            "2026-06-13": [
                {
                    "topic": "international relations",
                    "retrieval_memory": {
                        "argue_node": {
                            "store_queries": {"reasoning_db": "burden clash rebuttal mechanism"},
                            "key_terms": ["sovereignty", "deterrence"],
                            "source_refs": ["https://example.com/ir"],
                        }
                    },
                }
            ],
            "2026-06-12": [
                {
                    "topic": "feminism",
                    "retrieval_memory": {
                        "argue_node": {
                            "store_queries": {"reasoning_db": "intersectionality backlash"},
                            "key_terms": ["gender"],
                            "source_refs": ["https://example.com/fem"],
                        }
                    },
                }
            ],
        },
    )

    memory = recall_retrieval_memory("international relations", "argue_node")

    assert "reasoning_db" in memory["store_queries"]
    assert "sovereignty" in memory["key_terms"]


def test_query_plan_augments_queries_with_retrieval_memory(monkeypatch):
    monkeypatch.setattr(
        "rag.query_planner.recall_retrieval_memory",
        lambda topic, node_name: {
            "store_queries": {"reasoning_db": "deterrence security dilemma"},
            "key_terms": ["sovereignty", "precedent"],
            "source_refs": [],
        },
    )

    state = {
        "topic": "international relations",
        "lead_case": {"title": "Ukraine sovereignty and NATO expansion"},
        "topic_info": {},
    }

    plan = build_query_plan("argue_node", state)

    assert "deterrence security dilemma" in plan["store_queries"]["reasoning_db"]
    assert "sovereignty precedent" in plan["store_queries"]["reasoning_db"]


def test_source_performance_summary_prefers_stronger_related_sources(monkeypatch):
    monkeypatch.setattr(
        "rag.retrieval_memory.load_log",
        lambda: {
            "2026-06-14": [
                {
                    "topic": "international relations",
                    "concepts": ["sovereignty deterrence legitimacy"],
                    "top_articles": ["Ukraine case", "Sanctions case"],
                    "key_facts": ["fact one", "fact two"],
                    "vocab_words": ["credible", "robust", "coherent"],
                    "retrieval_memory": {
                        "argue_node": {
                            "source_refs": ["https://example.com/good"],
                            "source_scores": {"https://example.com/good": 1.0},
                        }
                    },
                },
                {
                    "topic": "international relations",
                    "concepts": [],
                    "top_articles": [],
                    "key_facts": [],
                    "vocab_words": [],
                    "retrieval_memory": {
                        "argue_node": {
                            "source_refs": ["https://example.com/weak"],
                            "source_scores": {"https://example.com/weak": 0.1},
                        }
                    },
                },
            ]
        },
    )

    summary = source_performance_summary("international relations", "argue_node")

    assert "https://example.com/good" in summary["preferred_sources"]


def test_query_plan_includes_source_performance_hints(monkeypatch):
    monkeypatch.setattr(
        "rag.query_planner.recall_retrieval_memory",
        lambda topic, node_name: {
            "store_queries": {"reasoning_db": "deterrence security dilemma"},
            "key_terms": ["sovereignty", "precedent"],
            "source_refs": [],
        },
    )
    monkeypatch.setattr(
        "rag.query_planner.source_performance_summary",
        lambda topic, node_name: {
            "preferred_sources": ["https://example.com/good"],
            "weak_sources": ["https://example.com/weak"],
            "source_rankings": [],
        },
    )

    plan = build_query_plan(
        "argue_node",
        {"topic": "international relations", "lead_case": {"title": "Ukraine sovereignty and NATO expansion"}, "topic_info": {}},
    )

    assert "https://example.com/good" in plan["metadata_hints"]["preferred_sources"]
    assert "https://example.com/weak" in plan["metadata_hints"]["weak_sources"]


def test_chunk_score_uses_source_preference_hints():
    chunk = {
        "page_content": "Sovereignty and deterrence matter for stability.",
        "metadata": {
            "url": "https://example.com/good",
            "source_class": "debate_theory",
            "topic_family": "international relations",
            "time_scope": "durable",
            "debate_utility": ["mechanism"],
            "source_quality": "high",
        },
    }
    plan = {
        "preferred_stores": ["reasoning_db"],
        "metadata_hints": {
            "source_classes": ["debate_theory"],
            "topic_family": "international relations",
            "time_scope": "durable",
            "debate_utility": ["mechanism"],
            "preferred_sources": ["https://example.com/good"],
            "weak_sources": [],
        },
    }

    boosted = chunk_score(chunk, "sovereignty deterrence mechanism", plan, "reasoning_db")

    penalized_plan = {
        "preferred_stores": ["reasoning_db"],
        "metadata_hints": {
            "source_classes": ["debate_theory"],
            "topic_family": "international relations",
            "time_scope": "durable",
            "debate_utility": ["mechanism"],
            "preferred_sources": [],
            "weak_sources": ["https://example.com/good"],
        },
    }
    penalized = chunk_score(chunk, "sovereignty deterrence mechanism", penalized_plan, "reasoning_db")

    assert boosted > penalized
