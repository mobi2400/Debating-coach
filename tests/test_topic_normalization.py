from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.format_node import format_node
from agents.rank_node import rank_node
from core.topic_utils import topic_name
from main import _initial_state


def run_topic_normalization_test():
    structured_topic = {
        "topic": "geopolitics",
        "debate_frames": ["power transition", "resource competition"],
    }

    assert topic_name(structured_topic) == "geopolitics"

    state = _initial_state(structured_topic)
    assert state["topic"] == "geopolitics"

    state["raw_articles"] = [
        {
            "title": "Geopolitics of chip controls",
            "url": "https://example.com/chips",
            "content": "This piece covers state power, technology, sanctions, and export controls.",
            "source": "test",
            "published": "",
        }
    ]
    ranked = rank_node(state)
    assert ranked["ranked_articles"], "rank_node should handle structured topic input safely"

    ranked["enriched_context"] = "Power transition and technology competition matter here."
    ranked["summaries"] = ["- Export controls reshape strategic leverage."]
    ranked["arguments"] = {
        "for": ["Controls preserve security."],
        "against": ["Controls fragment markets."],
        "middle": "Use narrow controls with clear thresholds.",
    }
    formatted = format_node(ranked)
    assert formatted["final_doc"].startswith("TOPIC: GEOPOLITICS")
    print("Topic normalization checks passed.")


if __name__ == "__main__":
    run_topic_normalization_test()
