import json
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

# Absolute path so the log lands in the project regardless of cwd.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = _PROJECT_ROOT / "memory" / "weekly_log.json"


def _ensure_log_file():
    if not LOG_FILE.exists():
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.write_text("{}", encoding="utf-8")


def load_log() -> dict:
    _ensure_log_file()
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        # Corrupt or unreadable log — fall back to empty rather than crash.
        print(f"[weekly_store] load_log failed ({exc}); using empty log.")
        return {}


def save_log(log: dict):
    """Atomic write: serialize to temp file in the same directory, then os.replace."""
    _ensure_log_file()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".weekly_log.", suffix=".json.tmp", dir=str(LOG_FILE.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(log, handle, indent=2)
        os.replace(tmp_path, LOG_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


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
            "english_lesson": content_dict.get("english_lesson", ""),
            "vocab_words": content_dict.get("vocab_words", []),
            "word_roots": content_dict.get("word_roots", []),
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


def mark_english_quiz(date_str: str, score: int):
    log = load_log()
    if date_str not in log:
        log[date_str] = [{"topic": "english", "timestamp": datetime.now().isoformat()}]
    for entry in log[date_str]:
        entry["english_quiz_score"] = score
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
