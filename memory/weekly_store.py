import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def _now_iso() -> str:
    """UTC timestamp so dev machines and GH Actions runners agree."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

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

    def _shorten_text(value: str, limit: int) -> str:
        text = " ".join(str(value).split())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _compact_list(items: list, limit: int, item_limit: int) -> list[str]:
        compacted = []
        for item in items[:limit]:
            compacted.append(_shorten_text(str(item), item_limit))
        return compacted

    arguments = content_dict.get("arguments", {}) or {}
    compact_arguments = {
        "for": _compact_list(arguments.get("for", []), 1, 220),
        "against": _compact_list(arguments.get("against", []), 1, 220),
        "middle": _shorten_text(arguments.get("middle", ""), 240),
    }

    top_articles = []
    for article in content_dict.get("ranked_articles", [])[:2]:
        title = article.get("title")
        if title:
            top_articles.append(_shorten_text(title, 140))

    new_entry = {
        "topic": topic,
        "selector_reason": _shorten_text(content_dict.get("selector_reason", ""), 140),
        "pre_knowledge": _compact_list(content_dict.get("pre_knowledge", []), 2, 220),
        "top_articles": top_articles,
        "summaries": _compact_list(content_dict.get("summaries", []), 2, 220),
        "arguments": compact_arguments,
        "key_facts": _compact_list(content_dict.get("key_facts", []), 2, 220),
        "concepts": _compact_list(content_dict.get("concepts", []), 3, 140),
        "debate_angle": _shorten_text(content_dict.get("debate_angle", ""), 520),
        "english_lesson": _shorten_text(content_dict.get("english_lesson", ""), 420),
        "vocab_words": _compact_list(content_dict.get("vocab_words", []), 3, 32),
        "word_roots": _compact_list(content_dict.get("word_roots", []), 2, 24),
        "studied": False,
        "quiz_score": None,
        "timestamp": _now_iso(),
    }

    replaced = False
    for index, entry in enumerate(log[today]):
        if str(entry.get("topic", "")).strip().lower() == topic.strip().lower():
            studied = entry.get("studied", False)
            quiz_score = entry.get("quiz_score")
            english_quiz_score = entry.get("english_quiz_score")
            new_entry["studied"] = studied
            new_entry["quiz_score"] = quiz_score
            if english_quiz_score is not None:
                new_entry["english_quiz_score"] = english_quiz_score
            log[today][index] = new_entry
            replaced = True
            break

    if not replaced:
        log[today].append(new_entry)

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
        log[date_str] = [{"topic": "english", "timestamp": _now_iso()}]
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
