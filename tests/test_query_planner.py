from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.metadata import build_metadata
from rag.query_planner import build_query_plan


def test_build_query_plan_for_argue_node():
    state = {
        "topic": "international relations",
        "lead_case": {"title": "Ukraine sovereignty and NATO expansion"},
        "topic_info": {
            "essential_theoretical_frameworks": [
                "Realism: states are rational actors pursuing survival in an anarchic system."
            ],
            "the_mechanisms_to_understand": [
                "How the international system produces conflict even when no actor wants war — the security dilemma"
            ],
            "argument_angles_most_debaters_miss": [
                "The double standard argument — when powerful states violate the norms they enforce on others"
            ],
        },
    }

    plan = build_query_plan("argue_node", state)

    assert plan["intent"] == "argument_generation"
    assert "reasoning_db" in plan["preferred_stores"]
    assert "burden clash rebuttal mechanism" in plan["store_queries"]["reasoning_db"]
    assert "mechanism" in plan["metadata_hints"]["debate_utility"]


def test_build_metadata_enriches_generic_fields():
    metadata = build_metadata(
        "news",
        "https://www.theatlantic.com/world/example-story",
        {"url": "https://www.theatlantic.com/world/example-story", "title": "International relations and NATO"},
    )

    assert metadata["source_class"] == "article"
    assert metadata["time_scope"] == "recent"
    assert metadata["source_domain"] == "www.theatlantic.com"
    assert metadata["topic_family"] == "international relations"
