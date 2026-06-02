import argparse
import json

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily"], required=True)
    parser.add_argument("--topic", type=str, default=None)
    args = parser.parse_args()

    if args.mode == "daily":
        run_daily(args.topic)
