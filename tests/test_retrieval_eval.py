from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.rag.fixtures import RETRIEVAL_EVAL_CASES
from evals.rag.retrieval_eval import evaluate_query_plan, evaluate_structured_evidence
from rag.metadata import build_metadata
from rag.query_planner import build_query_plan


def _chunk(text: str, metadata: dict) -> dict:
    return {"page_content": text, "metadata": metadata}


def test_retrieval_eval_cases_score_well_against_query_planner():
    for case in RETRIEVAL_EVAL_CASES:
        plan = build_query_plan(case["node_name"], case["state"])
        score = evaluate_query_plan(plan, case["expected"])
        assert score["total_score"] >= 0.7, f"{case['name']} scored too low: {score}"


def test_structured_evidence_eval_detects_required_sections():
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

    score = evaluate_structured_evidence(chunks, expected_sections=["definitions", "mechanisms", "examples"])

    assert score["section_score"] == 1.0
    assert score["present_sections"] == ["definitions", "examples", "mechanisms"]
