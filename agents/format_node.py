from agents.rank_node import _is_news_article, _is_reference_article
from core.topic_utils import topic_name
from memory.weekly_store import save_daily_digest


def _join_lines(lines: list[str]) -> str:
    return "\n".join(line for line in lines if line)


FINAL_DOC_CHAR_LIMIT = 1450


def _trim_block(text: str, char_limit: int, line_limit: int | None = None) -> str:
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    if line_limit is not None:
        lines = lines[:line_limit]
    compact = " ".join(lines)
    if len(compact) <= char_limit:
        return compact
    return compact[: char_limit - 3].rstrip() + "..."


def _sentences(text: str, limit: int = 2) -> list[str]:
    parts = []
    for raw in str(text).replace("\n", " ").split(". "):
        sentence = " ".join(raw.split()).strip(" -")
        if sentence:
            parts.append(sentence.rstrip(".") + ".")
        if len(parts) >= limit:
            break
    return parts


def _pre_knowledge_points(state: dict) -> list[str]:
    reference_background = str(state.get("reference_background", "")).strip()
    if reference_background:
        return _sentences(reference_background, limit=2)

    enriched = str(state.get("enriched_context", ""))
    cleaned_lines = []
    for line in enriched.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith(":") and stripped.isupper():
            continue
        if stripped.startswith("[source:") or stripped == "---":
            continue
        cleaned_lines.append(stripped)
        if len(cleaned_lines) >= 4:
            break

    cleaned_text = " ".join(cleaned_lines)
    points = _sentences(cleaned_text, limit=2)
    if points:
        return [_trim_block(point, 150) for point in points]

    concepts = state.get("concepts", [])[:2]
    if concepts:
        return [f"Know the concept '{_trim_block(concept, 80)}' before using it in today's case." for concept in concepts]
    return []


def _pick_lede(ranked_articles: list[dict]) -> dict | None:
    """TODAY'S CASE should always lead with a current-affairs piece when
    one is available — Wikipedia / Britannica entries are useful as
    background but read as filler at the top of a debate digest."""
    if not ranked_articles:
        return None
    for article in ranked_articles:
        if _is_news_article(article):
            return article
    for article in ranked_articles:
        if not _is_reference_article(article):
            return article
    return ranked_articles[0]


def _today_case_lines(state: dict) -> list[str]:
    ranked_articles = state.get("ranked_articles", [])
    article = _pick_lede(ranked_articles)
    if article is None:
        return ["No strong live article was retrieved today, so focus on the core framework and debate angles."]

    lines = [article.get("title", "Untitled article")]
    lines.extend(_sentences(article.get("content", ""), limit=2))
    return lines


def _argument_lines(state: dict) -> list[str]:
    arguments = state.get("arguments", {})
    lines = []
    if arguments.get("for"):
        lines.append(f"For: {_trim_block(arguments['for'][0], 130)}")
    if arguments.get("against"):
        lines.append(f"Against: {_trim_block(arguments['against'][0], 130)}")
    middle = arguments.get("middle")
    if middle:
        lines.append(f"Middle: {_trim_block(middle, 150)}")
    return lines[:3] or ["Build the clash by comparing mechanism, incentives, and long-term impact."]


def _recall_lines(state: dict) -> list[str]:
    topic = topic_name(state.get("topic"))
    concept = (state.get("concepts") or ["the central concept"])[0]
    fact = (state.get("key_facts") or ["the strongest example from today's material"])[0]
    return [
        f"In one sentence, explain why {_trim_block(concept, 80)} matters in {topic}.",
        f"Use this fact in a rebuttal: {_trim_block(fact, 110)}",
    ]


def _heuristic_format(state: dict) -> str:
    topic = topic_name(state.get("topic"))
    pre_knowledge = _pre_knowledge_points(state)
    case_lines = _today_case_lines(state)
    argument_lines = _argument_lines(state)
    recall_lines = _recall_lines(state)
    pre_lines = [f"- {item}" for item in pre_knowledge] if pre_knowledge else ["- No background context retrieved yet."]
    case_rendered = [f"- {item}" for item in case_lines]
    argument_rendered = [f"- {item}" for item in argument_lines]
    recall_rendered = [f"- {item}" for item in recall_lines]

    lines = [
        f"TOPIC: {topic.upper()}",
        f"Why today: {state.get('selector_reason', 'Priority topic rotation.')}",
        "",
        "PRE-KNOWLEDGE",
        *pre_lines,
        "",
        "TODAY'S CASE",
        *case_rendered,
        "",
        "DEBATE ANGLES",
        *argument_rendered,
        "",
        "COACH NOTE",
        _trim_block(state.get("debate_angle", "No coaching block generated."), 280),
        "",
        "ENGLISH POWER",
        _trim_block(state.get("english_lesson", "No English lesson generated."), 240, line_limit=6),
        "",
        "2-MINUTE RECALL",
        *recall_rendered,
    ]
    output = _join_lines(lines).strip()
    return _trim_block(output, FINAL_DOC_CHAR_LIMIT)


def format_node(state: dict) -> dict:
    state["task_type"] = "format"
    topic = topic_name(state.get("topic"))
    state["final_doc"] = _heuristic_format(state)

    save_daily_digest(
        topic,
        {
            "selector_reason": state.get("selector_reason", ""),
            "pre_knowledge": _pre_knowledge_points(state),
            "ranked_articles": state.get("ranked_articles", []),
            "summaries": state.get("summaries", []),
            "arguments": state.get("arguments", {}),
            "key_facts": state.get("key_facts", []),
            "concepts": state.get("concepts", []),
            "debate_angle": state.get("debate_angle", ""),
            "english_lesson": state.get("english_lesson", ""),
            "vocab_words": state.get("vocab_words", []),
            "word_roots": state.get("word_roots", []),
        },
    )

    return state
