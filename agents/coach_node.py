from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node


MAX_RAG_CHARS = 2500


def _heuristic_coach(topic: str, arguments: dict, summaries: list[str], rag_context: str) -> str:
    opening = arguments.get("for", [f"{topic.title()} is best opened through a fairness frame."])[0]
    rebuttal_target = arguments.get("against", ["Challenge the biggest tradeoff claim."])[0]
    style_hint = (
        "Borrow the rhythm and compression patterns from your stored style examples."
        if rag_context
        else "Keep the tone sharp, comparative, and easy to deliver under time pressure."
    )

    summary_anchor = summaries[0].splitlines()[0].lstrip("- ").strip() if summaries else f"Anchor your framing on the biggest practical consequence in {topic}."

    return "\n".join(
        [
            f"UNIQUE ANGLE: Frame {topic} as a clash between principle and implementation, then win on whichever side has better long-term incentives.",
            f"OPEN WITH THIS: {opening}",
            f"CLAIM-WARRANT-IMPACT: Claim the debate turns on {summary_anchor}. Warrant it with mechanism and actor incentives. Impact it in terms of fairness, stability, and scale.",
            f"TOP REBUTTAL: If they say '{rebuttal_target}', answer by questioning comparative world, feasibility, and hidden tradeoffs.",
            "POWER PHRASES: 'Follow the incentive structure.' | 'Compare worlds, not slogans.' | 'The mechanism matters more than the headline.' | 'Principle without implementation is empty.' | 'Win the weighing, win the round.'",
            f"STYLE NOTE: {style_hint}",
        ]
    )


def coach_node(state: dict) -> dict:
    state["task_type"] = "debate"
    topic = topic_name(state.get("topic"))
    rag_chunks = retrieve_for_node("coach_node", topic)
    rag_context = format_retrieved_context(rag_chunks)

    default_coaching = _heuristic_coach(
        topic,
        state.get("arguments", {}),
        state.get("summaries", []),
        rag_context,
    )

    if not state.get("summaries") and not rag_context:
        state["debate_angle"] = default_coaching
        return state

    prompt = (
        "You are a debate coach writing in the user's preferred debate style.\n"
        "Produce a compact coaching block with these sections exactly:\n"
        "UNIQUE ANGLE, OPEN WITH THIS, CLAIM-WARRANT-IMPACT, TOP REBUTTALS, POWER PHRASES.\n\n"
        f"Topic: {topic}\n"
        f"Summaries: {state.get('summaries', [])}\n"
        f"Arguments: {state.get('arguments', {})}\n"
        f"Style RAG context: {rag_context[:MAX_RAG_CHARS]}"
    )

    try:
        llm = get_llm_with_fallback(state)
        response = cached_invoke(llm, prompt, scope="coach")
        content = getattr(response, "content", response)
        state["debate_angle"] = str(content).strip() or default_coaching
    except Exception:
        state["debate_angle"] = default_coaching

    return state
