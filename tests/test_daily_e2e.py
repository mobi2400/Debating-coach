"""End-to-end test for the daily graph against topics.json.

Stubs out the four research tools and the LLM pool so we exercise the
full graph (research -> rag_enrich -> filter -> rank -> summarize ->
argue -> coach -> english_coach -> format) and the topics.json loader
without spending a single API call. Designed to run in CI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("DEBATEIQ_PROMPT_CACHE", "0")


def _stub_tools():
    from tools import ddg_tool, rss_tool, tavily_tool, wiki_tool

    sample = [
        {
            "title": "Feminism debates focus on autonomy and access",
            "url": "https://example.com/a",
            "content": (
                "Feminism debates often turn on access to opportunity and economic participation. "
                "Modern coverage highlights structural barriers, policy responses, and value clashes."
            ),
            "source": "stub",
            "published": "",
        },
        {
            "title": "Mechanism vs impact framing in policy debate",
            "url": "https://example.com/b",
            "content": (
                "Comparative weighing helps debaters choose mechanism over slogan. "
                "Case studies in labor and education reveal tradeoffs across institutions."
            ),
            "source": "stub",
            "published": "",
        },
    ]

    tavily_tool.tavily_search = lambda query: list(sample)
    wiki_tool.wiki_search = lambda query: {
        "title": query,
        "url": "https://en.wikipedia.org/wiki/Feminism",
        "content": "Feminism is a movement aimed at establishing equality across genders.",
        "source": "wikipedia",
        "published": "",
    }
    rss_tool.rss_fetch = lambda query, hours_back=24: []
    ddg_tool.ddg_search = lambda query: []


class _FakeLLM:
    def __init__(self, name: str):
        self.model = name

    def invoke(self, prompt: str):
        text = prompt.lower()
        # Check most specific phrases first; nodes pass each other's data in their
        # own prompts, so we can't dispatch on substrings like "for" or "arguments".
        if "format the debate digest" in text:
            return type("R", (), {"content": (
                "TOPIC: FEMINISM\n\nBACKGROUND\nStub background.\n\n"
                "TOP ARTICLES\n1. Stub\n\nSUMMARY BULLETS\n- point one\n\n"
                "ARGUMENTS FOR\n- A1\n\nARGUMENTS AGAINST\n- B1\n\n"
                "MIDDLE GROUND\nBoth sides have weight.\n\n"
                "COACH SECTION\nUNIQUE ANGLE\n\n"
                "ENGLISH POWER\nUse lucid.\n\n"
                "KEY FACTS\n- Participation rates.\n\n"
                "CONCEPTS TO REMEMBER\n- Structural inequality"
            )})()
        if "preferred debate style" in text or "produce a compact coaching block" in text:
            return type("R", (), {"content": (
                "UNIQUE ANGLE: Win on mechanism.\n"
                "OPEN WITH THIS: Lead with a comparative frame.\n"
                "CLAIM-WARRANT-IMPACT: Mechanism > slogan.\n"
                "TOP REBUTTALS: Address feasibility.\n"
                "POWER PHRASES: Compare worlds."
            )})()
        if "generating debate arguments" in text:
            return type("R", (), {"content": (
                '{"for": ["A1","A2","A3"],'
                ' "against": ["B1","B2","B3"],'
                ' "middle": "Both sides have weight; depend on mechanism."}'
            )})()
        if "word power made easy" in text:
            return type("R", (), {"content": (
                '{"english_lesson": "Use lucid for clarity.",'
                ' "vocab_words": ["lucid","precise","nuance"],'
                ' "word_roots": ["luc","cred"]}'
            )})()
        if "summarizing one article" in text:
            return type("R", (), {"content": (
                "SUMMARY:\n- point one\n- point two\n- point three\n\n"
                "KEY FACT: Participation rates shape outcomes.\n"
                "CONCEPT: Structural inequality"
            )})()
        if "ranking debate research" in text:
            return type("R", (), {"content": "[0, 1]"})()
        if "filtering research results" in text:
            return type("R", (), {"content": "[0, 1]"})()
        return type("R", (), {"content": "[]"})()


def _stub_pool():
    from core import fallback as fb
    from core import llm_pool

    fake_pool = {
        key: _FakeLLM(key)
        for key in ("fast", "balanced", "structured", "reasoning", "long_ctx", "best")
    }
    llm_pool.LLM_POOL = fake_pool
    fb.LLM_POOL = fake_pool


def run_daily_e2e_test():
    _stub_tools()
    _stub_pool()

    # Import after stubs so module-level singletons don't bind to real clients.
    from graph import build_daily_graph
    from main import _initial_state, _load_topics_config

    topics, metadata = _load_topics_config()
    assert isinstance(topics, list) and all(isinstance(t, str) for t in topics), (
        "topics loader must return a list of strings"
    )
    assert topics, "topics.json must yield at least one topic"
    print(f"Topics loaded: {len(topics)} (first: {topics[0]!r})")

    graph = build_daily_graph()
    result = graph.invoke(_initial_state(topics[0]))

    assert result["raw_articles"], "research_node should produce raw_articles"
    assert result["ranked_articles"], "rank_node should produce ranked_articles"
    assert result.get("topic_foundation"), "Phase 1 must populate topic_foundation"
    assert result.get("article_context"), "Phase 1 must populate article_context"
    assert result.get("preknowledge_notes"), "topic foundation should still populate legacy preknowledge notes"
    assert result["summaries"], "summarize_node should produce summaries"
    assert result["arguments"].get("for") and len(result["arguments"]["for"]) == 3
    assert result["arguments"].get("against") and len(result["arguments"]["against"]) == 3
    assert result["arguments"].get("middle"), "argue_node must yield a middle ground"
    assert "UNIQUE ANGLE" in result["debate_angle"], "coach_node must emit UNIQUE ANGLE"
    assert result["english_lesson"], "english_coach_node must populate english_lesson"
    final_doc = result["final_doc"]
    assert (
        "TOPIC:" in final_doc or "TOPIC FOR TODAY" in final_doc
    ), "format_node must emit a topic header"

    print("Daily e2e checks passed.")


if __name__ == "__main__":
    run_daily_e2e_test()
