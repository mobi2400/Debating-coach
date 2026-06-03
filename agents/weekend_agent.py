import json

from core.fallback import get_llm_with_fallback
from delivery.whatsapp import send_message
from memory.weekly_store import get_week_log


def _compute_stats(week_log: dict) -> tuple[int, int]:
    entries = [entry for day_entries in week_log.values() for entry in day_entries]
    days_studied = sum(1 for entry in entries if entry.get("studied"))
    scores = [entry["quiz_score"] for entry in entries if entry.get("quiz_score") is not None]
    average_score = int(sum(scores) / len(scores)) if scores else 0
    return days_studied, average_score


def _heuristic_weekend_knowledge(week_log: dict) -> dict:
    concepts = []
    frameworks = []
    key_stats = []
    argument_patterns = []

    for day_entries in week_log.values():
        for entry in day_entries:
            topic = entry.get("topic", "unknown topic")
            for concept in entry.get("concepts", [])[:2]:
                concepts.append(
                    {
                        "title": concept,
                        "what_it_is": f"A durable concept from {topic}.",
                        "why_it_matters_in_debate": "Useful for framing and comparative analysis.",
                        "remember_this": f"Link {concept} back to mechanism and impact.",
                        "source_topic": topic,
                    }
                )
            for fact in entry.get("key_facts", [])[:2]:
                key_stats.append(
                    {
                        "stat": fact,
                        "context": f"Fact retained from {topic}.",
                        "use_in_debate": "Use it as an anchor point in opening or rebuttal.",
                    }
                )

            frameworks.append(
                {
                    "title": f"{topic.title()} weighing frame",
                    "what_it_is": f"A repeatable lens for evaluating {topic}.",
                    "why_it_matters_in_debate": "Lets you compare worlds instead of isolated claims.",
                    "remember_this": "Mechanism first, then impact, then comparative weighing.",
                    "source_topic": topic,
                }
            )
            argument_patterns.append(
                {
                    "pattern_name": f"{topic.title()} tradeoff analysis",
                    "how_it_works": "Identify the benefit, expose the hidden cost, then compare magnitude and reversibility.",
                    "example": f"Use this when debating policy proposals inside {topic}.",
                }
            )

    return {
        "concepts": concepts[:6],
        "frameworks": frameworks[:4],
        "key_stats": key_stats[:6],
        "argument_patterns": argument_patterns[:4],
    }


def _line_from(item, primary_keys: list[str], detail_keys: list[str]) -> str:
    """Render an item that might be a dict (preferred) or a plain string."""
    if isinstance(item, str):
        return f"- {item}"
    if not isinstance(item, dict):
        return f"- {item!s}"
    primary = next((str(item.get(k)) for k in primary_keys if item.get(k)), "")
    detail = next((str(item.get(k)) for k in detail_keys if item.get(k)), "")
    if primary and detail:
        return f"- {primary}: {detail}"
    return f"- {primary or detail or item}"


def _format_weekend_message(knowledge: dict, days_studied: int, average_score: int) -> str:
    lines = [
        "WEEKLY BRAIN UPLOAD",
        "=" * 25,
        f"Days studied: {days_studied}",
        f"Average quiz score: {average_score}%",
        "",
    ]

    if knowledge.get("concepts"):
        lines.append("CONCEPTS")
        for item in knowledge["concepts"]:
            lines.append(_line_from(item, ["title", "name"], ["remember_this", "what_it_is"]))
        lines.append("")

    if knowledge.get("frameworks"):
        lines.append("FRAMEWORKS")
        for item in knowledge["frameworks"]:
            lines.append(_line_from(item, ["title", "name"], ["remember_this", "what_it_is"]))
        lines.append("")

    if knowledge.get("key_stats"):
        lines.append("KEY FACTS")
        for item in knowledge["key_stats"]:
            lines.append(_line_from(item, ["stat", "fact"], ["context", "use_in_debate"]))
        lines.append("")

    if knowledge.get("argument_patterns"):
        lines.append("ARGUMENT PATTERNS")
        for item in knowledge["argument_patterns"]:
            lines.append(_line_from(item, ["pattern_name", "name"], ["how_it_works", "example"]))

    return "\n".join(lines).strip()


def weekend_agent_node(state: dict) -> dict:
    state["task_type"] = "weekend"
    week_log = get_week_log()
    days_studied, average_score = _compute_stats(week_log)
    default_knowledge = _heuristic_weekend_knowledge(week_log)

    prompt = (
        "Filter this weekly debate memory into durable knowledge only.\n"
        "Return JSON with keys: concepts, frameworks, key_stats, argument_patterns.\n"
        "Exclude transient news and time-bound narratives.\n\n"
        f"Week log: {json.dumps(week_log, ensure_ascii=False)}"
    )

    knowledge = default_knowledge
    try:
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = str(getattr(response, "content", response)).strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content)
        # Only accept the parsed object if it has at least one of the lanes the
        # formatter expects; otherwise keep the heuristic so the digest is never empty.
        if isinstance(parsed, dict) and any(
            key in parsed for key in ("concepts", "frameworks", "key_stats", "argument_patterns")
        ):
            knowledge = {
                "concepts": parsed.get("concepts") or default_knowledge["concepts"],
                "frameworks": parsed.get("frameworks") or default_knowledge["frameworks"],
                "key_stats": parsed.get("key_stats") or default_knowledge["key_stats"],
                "argument_patterns": parsed.get("argument_patterns") or default_knowledge["argument_patterns"],
            }
    except Exception as exc:
        print(f"[Weekend] LLM parse failed: {exc}")

    final_message = _format_weekend_message(knowledge, days_studied, average_score)
    send_message(final_message)
    state["final_doc"] = final_message
    return state
