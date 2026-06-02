import argparse
import json

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "summarize-smoke"], required=True)
    parser.add_argument("--topic", type=str, default=None)
    args = parser.parse_args()

    if args.mode == "daily":
        run_daily(args.topic)
    elif args.mode == "summarize-smoke":
        run_summarize_smoke()
