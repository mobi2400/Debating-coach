from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.rag.real_trace_eval import evaluate_recent_traces


def test_evaluate_recent_traces_scores_recent_lessons(monkeypatch):
    monkeypatch.setattr(
        "evals.rag.real_trace_eval.load_log",
        lambda: {
            "2026-06-14": [
                {
                    "topic": "international relations",
                    "top_articles": ["Ukraine case", "Sanctions case"],
                    "key_facts": ["fact one", "fact two"],
                    "concepts": ["sovereignty", "deterrence", "legitimacy"],
                    "vocab_words": ["credible", "robust", "coherent"],
                    "retrieval_memory": {
                        "argue_node": {
                            "store_queries": {"reasoning_db": "burden clash rebuttal mechanism"},
                            "key_terms": ["sovereignty", "deterrence", "precedent"],
                            "source_refs": ["https://example.com/a", "https://example.com/b"],
                        },
                        "coach_node": {
                            "store_queries": {"style_db": "judge language weighing extension"},
                            "key_terms": ["weighing", "comparison"],
                            "source_refs": ["https://example.com/c"],
                        },
                    },
                }
            ],
            "2026-06-13": [
                {
                    "topic": "feminism",
                    "top_articles": ["Representation"],
                    "key_facts": ["fact one"],
                    "concepts": ["intersectionality"],
                    "vocab_words": ["normative"],
                    "retrieval_memory": {},
                }
            ],
        },
    )

    report = evaluate_recent_traces(limit_days=7)

    assert report["lessons_scored"] == 2
    assert report["average_score"] > 0
    assert "argue_node" in report["node_coverage"]
    assert any(item["topic"] == "international relations" for item in report["lesson_scores"])


def test_evaluate_recent_traces_flags_low_scoring_topics(monkeypatch):
    monkeypatch.setattr(
        "evals.rag.real_trace_eval.load_log",
        lambda: {
            "2026-06-14": [
                {
                    "topic": "weak topic",
                    "top_articles": [],
                    "key_facts": [],
                    "concepts": [],
                    "vocab_words": ["vocabulary"],
                    "retrieval_memory": {},
                }
            ]
        },
    )

    report = evaluate_recent_traces(limit_days=7)

    assert "weak topic" in report["low_scoring_topics"]
