from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from memory.weekly_store import save_daily_digest


def _join_lines(lines: list[str]) -> str:
    return "\n".join(line for line in lines if line)


def _heuristic_format(state: dict) -> str:
    topic = topic_name(state.get("topic"))
    arguments = state.get("arguments", {})
    lines = [
        f"TOPIC: {topic.upper()}",
        "=" * 28,
        "",
        "BACKGROUND",
        state.get("enriched_context", "")[:700] or "No background context retrieved yet.",
        "",
        "TOP ARTICLES",
    ]

    ranked_articles = state.get("ranked_articles", [])
    if ranked_articles:
        for index, article in enumerate(ranked_articles[:5], start=1):
            lines.append(f"{index}. {article.get('title', 'Untitled')}")
    else:
        lines.append("No ranked articles available in the current environment.")

    lines.extend(["", "SUMMARY BULLETS"])
    if state.get("summaries"):
        for summary in state["summaries"][:3]:
            lines.append(summary)
            lines.append("")
    else:
        lines.append("No summaries available.")

    lines.extend(["ARGUMENTS FOR"])
    lines.extend(f"- {item}" for item in arguments.get("for", []))
    lines.extend(["", "ARGUMENTS AGAINST"])
    lines.extend(f"- {item}" for item in arguments.get("against", []))
    lines.extend(["", "MIDDLE GROUND", arguments.get("middle", "No middle-ground argument generated."), ""])
    lines.extend(["COACH SECTION", state.get("debate_angle", "No coaching block generated.")])
    lines.extend(["", "ENGLISH POWER", state.get("english_lesson", "No English lesson generated.")])

    if state.get("key_facts"):
        lines.extend(["", "KEY FACTS"])
        lines.extend(f"- {fact}" for fact in state["key_facts"][:5])

    if state.get("concepts"):
        lines.extend(["", "CONCEPTS TO REMEMBER"])
        lines.extend(f"- {concept}" for concept in state["concepts"][:5])

    return _join_lines(lines).strip()


def format_node(state: dict) -> dict:
    state["task_type"] = "format"
    topic = topic_name(state.get("topic"))
    default_output = _heuristic_format(state)

    prompt = (
        "Format the debate digest for WhatsApp.\n"
        "Do not use markdown symbols like # or **.\n"
        "Use clean all-caps section labels, readable spacing, and concise phone-friendly output.\n"
        "The very first line MUST be exactly: TOPIC: <TOPIC IN UPPERCASE>\n"
        "Use these section headers verbatim and in this order: TOPIC:, BACKGROUND, TOP ARTICLES, "
        "SUMMARY BULLETS, ARGUMENTS FOR, ARGUMENTS AGAINST, MIDDLE GROUND, COACH SECTION, ENGLISH POWER, KEY FACTS, CONCEPTS TO REMEMBER.\n\n"
        f"Topic: {topic}\n"
        f"Ranked articles: {state.get('ranked_articles', [])}\n"
        f"Summaries: {state.get('summaries', [])}\n"
        f"Arguments: {state.get('arguments', {})}\n"
        f"Debate coaching: {state.get('debate_angle', '')}\n"
        f"English lesson: {state.get('english_lesson', '')}\n"
        f"Key facts: {state.get('key_facts', [])}\n"
        f"Concepts: {state.get('concepts', [])}"
    )

    try:
        llm = get_llm_with_fallback(state)
        response = cached_invoke(llm, prompt, scope="format")
        content = getattr(response, "content", response)
        state["final_doc"] = str(content).strip() or default_output
    except Exception:
        state["final_doc"] = default_output

    save_daily_digest(
        topic,
        {
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
