from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import fallback as fallback_module
from core.llm_router import ROUTING_MAP, route_by_task


BASE_STATE = {
    "topic": "feminism",
    "raw_articles": [],
    "enriched_context": "",
    "ranked_articles": [],
    "summaries": [],
    "key_facts": [],
    "concepts": [],
    "arguments": {},
    "debate_angle": "",
    "final_doc": "",
    "task_type": "fetch",
    "article_length": 0,
    "studied_today": None,
    "quiz_score": None,
}


class FakeLLM:
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail

    def invoke(self, _: str):
        if self.should_fail:
            raise RuntimeError(f"{self.name} unavailable")
        return "pong"


def print_routes():
    print("Route map:")
    for task_type, expected_key in ROUTING_MAP.items():
        state = {**BASE_STATE, "task_type": task_type}
        actual_key = route_by_task(state)
        print(f"  {task_type:<10} -> {actual_key}")
        assert actual_key == expected_key, (
            f"Task '{task_type}' routed to '{actual_key}', expected '{expected_key}'."
        )

    long_article_state = {**BASE_STATE, "task_type": "rank", "article_length": 9001}
    assert route_by_task(long_article_state) == "long_ctx"
    print("  long article override -> long_ctx")


def test_fallback():
    original_pool = fallback_module.LLM_POOL
    try:
        fallback_module.LLM_POOL = {
            "fast": FakeLLM("fast", should_fail=True),
            "balanced": FakeLLM("balanced"),
            "structured": FakeLLM("structured"),
            "reasoning": FakeLLM("reasoning"),
            "long_ctx": FakeLLM("long_ctx"),
            "best": FakeLLM("best"),
        }

        llm = fallback_module.get_llm_with_fallback({**BASE_STATE, "task_type": "filter"})
        assert isinstance(llm, FakeLLM)
        assert llm.name == "balanced"
        print("Fallback check:")
        print("  primary 'fast' failed -> fallback selected 'balanced'")
    finally:
        fallback_module.LLM_POOL = original_pool


if __name__ == "__main__":
    print_routes()
    test_fallback()
    print("Router checks passed.")
