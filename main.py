import argparse
import json

from agents.argue_node import argue_node
from agents.coach_node import coach_node
from agents.summarize_node import summarize_node
from graph import build_daily_graph


def _initial_state(topic: str) -> dict:
    return {
        "topic": topic,
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


def run_daily(topic_override: str | None = None):
    with open("topics.json", "r", encoding="utf-8") as handle:
        topics = json.load(handle)

    if topic_override:
        topics = [topic_override]

    graph = build_daily_graph()

    for topic in topics:
        print(f"\n{'=' * 40}")
        print(f"Processing topic: {topic}")
        print(f"{'=' * 40}")
        result = graph.invoke(_initial_state(topic))
        print(f"Raw articles: {len(result['raw_articles'])}")
        print(f"Ranked articles: {len(result['ranked_articles'])}")
        print(f"Enriched context chars: {len(result['enriched_context'])}")


def run_summarize_smoke():
    state = _initial_state("feminism")
    state["ranked_articles"] = [
        {
            "title": "Sample article",
            "url": "https://example.com",
            "content": "Feminism debates often focus on equality, representation, and policy impact. "
            "Recent coverage discusses economic participation and legal safeguards. "
            "Debaters can use this to compare principle and outcome based framing.",
            "source": "sample",
            "published": "",
        }
    ]
    state["enriched_context"] = "Sample background context."
    result = summarize_node(state)
    print(f"Summaries: {len(result['summaries'])}")
    print(f"Key facts: {len(result['key_facts'])}")
    print(f"Concepts: {len(result['concepts'])}")


def run_argue_smoke():
    state = _initial_state("feminism")
    state["summaries"] = [
        "- Equality claims often hinge on access to opportunity.\n- Economic participation shapes autonomy."
    ]
    result = argue_node(state)
    print(f"FOR arguments: {len(result['arguments'].get('for', []))}")
    print(f"AGAINST arguments: {len(result['arguments'].get('against', []))}")
    print(f"Middle present: {bool(result['arguments'].get('middle'))}")


def run_coach_smoke():
    state = _initial_state("feminism")
    state["summaries"] = [
        "- Equality debates turn on access to opportunity.\n- Economic autonomy strengthens broader freedom."
    ]
    state["arguments"] = {
        "for": ["Feminism expands access and voice.", "It reduces structural barriers.", "It improves autonomy."],
        "against": ["Implementation can create backlash.", "Bad policy design can misfire.", "Tradeoffs still matter."],
        "middle": "Support the principle but scrutinize mechanisms.",
    }
    result = coach_node(state)
    print(f"Coaching chars: {len(result['debate_angle'])}")
    print(f"Contains UNIQUE ANGLE: {'UNIQUE ANGLE' in result['debate_angle']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "summarize-smoke", "argue-smoke", "coach-smoke"], required=True)
    parser.add_argument("--topic", type=str, default=None)
    args = parser.parse_args()

    if args.mode == "daily":
        run_daily(args.topic)
    elif args.mode == "summarize-smoke":
        run_summarize_smoke()
    elif args.mode == "argue-smoke":
        run_argue_smoke()
    elif args.mode == "coach-smoke":
        run_coach_smoke()
