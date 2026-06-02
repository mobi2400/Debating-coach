from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.weekend_agent import _compute_stats, _format_weekend_message, _heuristic_weekend_knowledge


def run_weekend_test():
    mock_week = {
        "2026-06-01": [
            {
                "topic": "feminism",
                "concepts": ["intersectionality"],
                "key_facts": ["Representation affects policy priorities."],
                "studied": True,
                "quiz_score": 80,
            }
        ],
        "2026-05-31": [
            {
                "topic": "geopolitics",
                "concepts": ["deterrence"],
                "key_facts": ["Security guarantees alter bargaining behavior."],
                "studied": False,
                "quiz_score": None,
            }
        ],
    }

    days_studied, average_score = _compute_stats(mock_week)
    assert days_studied == 1
    assert average_score == 80

    knowledge = _heuristic_weekend_knowledge(mock_week)
    assert knowledge["concepts"]
    assert knowledge["frameworks"]
    assert knowledge["argument_patterns"]

    message = _format_weekend_message(knowledge, days_studied, average_score)
    assert "WEEKLY BRAIN UPLOAD" in message
    assert "intersectionality" in message
    print("Weekend checks passed.")


if __name__ == "__main__":
    run_weekend_test()
