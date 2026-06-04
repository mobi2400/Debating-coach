from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory import weekly_store
from agents.topic_selector import choose_topic_for_today


def run_memory_test():
    original_log_file = weekly_store.LOG_FILE
    temp_log = PROJECT_ROOT / "memory" / "weekly_log.test.json"
    weekly_store.LOG_FILE = temp_log

    try:
        if temp_log.exists():
            temp_log.unlink()

        payload = {
            "summaries": ["Summary"],
            "arguments": {"for": ["A"], "against": ["B"], "middle": "C"},
            "key_facts": ["Fact"],
            "concepts": ["Concept"],
            "debate_angle": "Angle",
            "english_lesson": "ENGLISH POWER",
            "vocab_words": ["lucid"],
            "word_roots": ["dict"],
            "selector_reason": "Least recently studied priority topic.",
            "pre_knowledge": ["Know realism vs liberalism."],
            "ranked_articles": [{"title": "Why sanctions reshape leverage"}],
        }

        weekly_store.save_daily_digest("feminism", payload)
        log = weekly_store.load_log()
        assert str(date.today()) in log
        assert log[str(date.today())][0]["topic"] == "feminism"

        weekly_store.mark_as_studied(str(date.today()), True, 80)
        updated = weekly_store.load_log()
        assert updated[str(date.today())][0]["studied"] is True
        assert updated[str(date.today())][0]["quiz_score"] == 80
        assert updated[str(date.today())][0]["english_lesson"] == "ENGLISH POWER"
        assert updated[str(date.today())][0]["vocab_words"] == ["lucid"]
        assert updated[str(date.today())][0]["selector_reason"]
        assert updated[str(date.today())][0]["pre_knowledge"] == ["Know realism vs liberalism."]
        assert updated[str(date.today())][0]["top_articles"] == ["Why sanctions reshape leverage"]

        week_log = weekly_store.get_week_log()
        assert str(date.today()) in week_log

        weekly_store.mark_english_quiz(str(date.today()), 75)
        updated_again = weekly_store.load_log()
        assert updated_again[str(date.today())][0]["english_quiz_score"] == 75

        weekly_store.save_daily_digest("feminism", payload)
        deduped = weekly_store.load_log()
        assert len(deduped[str(date.today())]) == 1

        # Selector should avoid repeating the most recently studied topic.
        choice = choose_topic_for_today(
            [{"topic": "feminism"}, {"topic": "geopolitics"}, {"topic": "education"}]
        )
        assert choice["topic"] != "feminism"

        print("Memory checks passed.")
    finally:
        weekly_store.LOG_FILE = original_log_file
        if temp_log.exists():
            temp_log.unlink()


if __name__ == "__main__":
    run_memory_test()
