from __future__ import annotations

from collections import Counter
from datetime import date, datetime

from memory.weekly_store import load_log


def _latest_topic_dates() -> tuple[dict[str, date], Counter]:
    log = load_log()
    latest: dict[str, date] = {}
    counts: Counter = Counter()

    for day, entries in log.items():
        try:
            day_value = datetime.fromisoformat(f"{day}T00:00:00").date()
        except Exception:
            continue

        day_topics = {
            str(entry.get("topic", "")).strip().lower()
            for entry in entries
            if str(entry.get("topic", "")).strip()
        }
        spaced_day = len(day_topics) <= 1

        for entry in entries:
            topic = str(entry.get("topic", "")).strip().lower()
            if not topic:
                continue
            counts[topic] += 1
            if spaced_day:
                previous = latest.get(topic)
                if previous is None or day_value > previous:
                    latest[topic] = day_value

    return latest, counts


def choose_topic_for_today(topic_entries: list[str | dict]) -> dict:
    candidates = []
    for index, entry in enumerate(topic_entries):
        if isinstance(entry, str):
            name = entry.strip()
            topic_info = {"topic": name}
        elif isinstance(entry, dict):
            name = str(entry.get("topic", "")).strip()
            topic_info = entry
        else:
            continue
        if name:
            candidates.append((index, name, topic_info))

    if not candidates:
        raise ValueError("No valid topics available for selection.")

    latest_dates, counts = _latest_topic_dates()
    today = date.today()

    def rank(candidate):
        index, name, _topic_info = candidate
        key = name.lower()
        latest = latest_dates.get(key)
        days_since = 9999 if latest is None else max((today - latest).days, 0)
        appearances = counts.get(key, 0)
        seen_today_penalty = 1 if latest == today else 0
        return (
            seen_today_penalty,
            -days_since,
            appearances,
            index,
        )

    _index, chosen_name, chosen_info = min(candidates, key=rank)
    latest = latest_dates.get(chosen_name.lower())
    if latest is None:
        reason = "New priority topic that has not been studied yet."
    else:
        gap = max((today - latest).days, 0)
        reason = f"Least recently studied priority topic ({gap} day gap)."

    return {
        "topic": chosen_name,
        "reason": reason,
        "topic_info": chosen_info,
    }
