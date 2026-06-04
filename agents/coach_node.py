from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node


MAX_RAG_CHARS = 900
MAX_SUMMARIES = 2


def _topic_info_list(topic_info: dict, key: str, limit: int = 2) -> list[str]:
    values = topic_info.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()][:limit]


def _heuristic_coach(topic: str, arguments: dict, summaries: list[str], rag_context: str, topic_info: dict | None = None) -> str:
    topic_info = topic_info or {}
    opening = arguments.get("for", [f"{topic.title()} is best opened through a fairness frame."])[0]
    rebuttal_target = arguments.get("against", ["Challenge the biggest tradeoff claim."])[0]
    style_hint = (
        "Borrow the rhythm and compression patterns from your stored style examples."
        if rag_context
        else "Keep the tone sharp, comparative, and easy to deliver under time pressure."
    )
    summary_anchor = summaries[0].splitlines()[0].lstrip("- ").strip() if summaries else f"Anchor your framing on the biggest practical consequence in {topic}."
    frameworks = _topic_info_list(topic_info, "essential_theoretical_frameworks", 1)
    concepts = _topic_info_list(topic_info, "key_concepts_own_these_precisely", 2)
    missed_angles = _topic_info_list(topic_info, "argument_angles_most_debaters_miss", 1)
    live_cases = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 1)
    recurring = _topic_info_list(topic_info, "recurring_motions_at_wudc_level", 1)

    unique_angle = (
        missed_angles[0]
        if missed_angles
        else f"Frame {topic} as a clash between principle and implementation, then win on whichever side has better long-term incentives."
    )
    opening_line = (
        f"{opening} Use {live_cases[0]} as the concrete proof that this is not abstract theory."
        if live_cases
        else opening
    )
    claim_block = (
        f"Claim the debate turns on {summary_anchor}. "
        f"Warrant it with {' and '.join(concepts[:2]) if concepts else 'mechanism and actor incentives'}. "
        f"Impact it in terms of fairness, stability, legitimacy, and precedent."
    )
    rebuttal = (
        f"If they say '{rebuttal_target}', answer by using {frameworks[0] if frameworks else 'comparative world analysis'} and then forcing them to defend second-order effects."
    )
    power_phrases = [
        "Compare worlds, not slogans.",
        "The mechanism matters more than the headline.",
        "Win the weighing, win the round.",
    ]
    if recurring:
        power_phrases.append(f"Think of this like the WUDC motion: {recurring[0]}")

    return "\n".join(
        [
            f"UNIQUE ANGLE: {unique_angle}",
            f"OPEN WITH THIS: {opening_line}",
            f"CLAIM-WARRANT-IMPACT: {claim_block}",
            f"TOP REBUTTAL: {rebuttal}",
            "POWER PHRASES: " + " | ".join(f"'{phrase}'" for phrase in power_phrases),
            f"STYLE NOTE: {style_hint}",
        ]
    )


def coach_node(state: dict) -> dict:
    state["task_type"] = "debate"
    topic = topic_name(state.get("topic"))
    topic_info = state.get("topic_info", {}) or {}
    rag_chunks = retrieve_for_node("coach_node", topic)
    rag_context = format_retrieved_context(rag_chunks)

    default_coaching = _heuristic_coach(
        topic,
        state.get("arguments", {}),
        state.get("summaries", [])[:MAX_SUMMARIES],
        rag_context,
        topic_info,
    )

    summaries = state.get("summaries", [])[:MAX_SUMMARIES]

    if not summaries and not rag_context:
        state["debate_angle"] = default_coaching
        return state

    prompt = (
        "You are a debate coach writing in the user's preferred debate style.\n"
        "Produce a compact coaching block with these sections exactly:\n"
        "UNIQUE ANGLE, OPEN WITH THIS, CLAIM-WARRANT-IMPACT, TOP REBUTTALS, POWER PHRASES.\n\n"
        f"Topic: {topic}\n"
        f"Summaries: {summaries}\n"
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
