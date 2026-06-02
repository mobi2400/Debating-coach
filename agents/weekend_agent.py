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
            lines.append(f"- {item['title']}: {item['remember_this']}")
        lines.append("")

    if knowledge.get("frameworks"):
        lines.append("FRAMEWORKS")
        for item in knowledge["frameworks"]:
            lines.append(f"- {item['title']}: {item['remember_this']}")
        lines.append("")

    if knowledge.get("key_stats"):
        lines.append("KEY FACTS")
        for item in knowledge["key_stats"]:
            lines.append(f"- {item['stat']}")
        lines.append("")

    if knowledge.get("argument_patterns"):
        lines.append("ARGUMENT PATTERNS")
        for item in knowledge["argument_patterns"]:
            lines.append(f"- {item['pattern_name']}: {item['how_it_works']}")

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

    try:
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        knowledge = json.loads(str(content))
    except Exception:
        knowledge = default_knowledge

    final_message = _format_weekend_message(knowledge, days_studied, average_score)
    send_message(final_message)
    state["final_doc"] = final_message
    return state
