import json
from datetime import date, datetime, timedelta
from pathlib import Path

LOG_FILE = Path("memory/weekly_log.json")


def _ensure_log_file():
    if not LOG_FILE.exists():
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.write_text("{}", encoding="utf-8")


def load_log() -> dict:
    _ensure_log_file()
    with open(LOG_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_log(log: dict):
    _ensure_log_file()
    with open(LOG_FILE, "w", encoding="utf-8") as handle:
        json.dump(log, handle, indent=2)


def save_daily_digest(topic: str, content_dict: dict):
    log = load_log()
    today = str(date.today())

    if today not in log:
        log[today] = []

    log[today].append(
        {
            "topic": topic,
            "summaries": content_dict.get("summaries", []),
            "arguments": content_dict.get("arguments", {}),
            "key_facts": content_dict.get("key_facts", []),
            "concepts": content_dict.get("concepts", []),
            "debate_angle": content_dict.get("debate_angle", ""),
            "studied": False,
            "quiz_score": None,
            "timestamp": datetime.now().isoformat(),
        }
    )

    save_log(log)


def mark_as_studied(date_str: str, studied: bool, score: int | None = None):
    log = load_log()
    if date_str in log:
        for entry in log[date_str]:
            entry["studied"] = studied
            if score is not None:
                entry["quiz_score"] = score
    save_log(log)


def get_week_log() -> dict:
    log = load_log()
    result = {}
    for offset in range(7):
        day = str(date.today() - timedelta(days=offset))
        if day in log:
            result[day] = log[day]
    return result


def get_today_log() -> list:
    log = load_log()
    return log.get(str(date.today()), [])
