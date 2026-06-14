import json

from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_bundle_for_node


MAX_RAG_CHARS = 900
MAX_SUMMARIES = 2


def _topic_info_list(topic_info: dict, key: str, limit: int = 2) -> list[str]:
    values = topic_info.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()][:limit]


def _build_debate_query(topic: str, topic_info: dict, summaries: list[str], arguments: dict) -> str:
    live_case = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 1)
    frameworks = _topic_info_list(topic_info, "essential_theoretical_frameworks", 2)
    concepts = _topic_info_list(topic_info, "key_concepts_own_these_precisely", 2)
    recurring = _topic_info_list(topic_info, "recurring_motions_at_wudc_level", 1)
    pieces = [
        topic,
        "value clash burden of proof mechanism rebuttal weighing WUDC matter file",
        summaries[0] if summaries else "",
        arguments.get("middle", ""),
        live_case[0] if live_case else "",
        " | ".join(frameworks),
        " | ".join(concepts),
        recurring[0] if recurring else "",
    ]
    return " ".join(piece for piece in pieces if piece).strip()


def _heuristic_debate_packet(topic: str, arguments: dict, summaries: list[str], topic_info: dict | None = None) -> dict:
    topic_info = topic_info or {}
    frameworks = _topic_info_list(topic_info, "essential_theoretical_frameworks", 1)
    concepts = _topic_info_list(topic_info, "key_concepts_own_these_precisely", 2)
    missed_angles = _topic_info_list(topic_info, "argument_angles_most_debaters_miss", 1)
    live_cases = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 1)
    recurring = _topic_info_list(topic_info, "recurring_motions_at_wudc_level", 1)
    mechanisms = _topic_info_list(topic_info, "the_mechanisms_to_understand", 2)
    opening = arguments.get("for", [f"{topic.title()} is best opened through a fairness frame."])[0]
    rebuttal_target = arguments.get("against", ["Challenge the biggest tradeoff claim."])[0]
    summary_anchor = summaries[0].splitlines()[0].lstrip("- ").strip() if summaries else f"Anchor your framing on the biggest practical consequence in {topic}."

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

    return {
        "unique_angle": unique_angle,
        "value_clash": (
            f"The deepest clash is between {concepts[0] if concepts else 'legitimacy'} and {concepts[1] if len(concepts) > 1 else 'order'}."
            if concepts
            else f"The deepest clash is between principle and implementation in {topic}."
        ),
        "burden_of_proof": (
            "Your burden is to prove not just that the principle sounds attractive, but that the mechanism survives contact with power, incentives, and precedent."
        ),
        "mechanism": (
            mechanisms[0]
            if mechanisms
            else "Track who has incentives to defect, who enforces the norm, and why that enforcement sticks."
        ),
        "open_with_this": opening_line,
        "claim_warrant_impact": claim_block,
        "top_rebuttal": rebuttal,
        "judge_language": "Tell the judge why your world is more likely, more stable, and less reversible in its harms.",
        "power_phrases": power_phrases,
    }


def _packet_to_block(packet: dict) -> str:
    return "\n".join(
        [
            f"UNIQUE ANGLE: {packet.get('unique_angle', '')}",
            f"VALUE CLASH: {packet.get('value_clash', '')}",
            f"BURDEN OF PROOF: {packet.get('burden_of_proof', '')}",
            f"MECHANISM: {packet.get('mechanism', '')}",
            f"OPEN WITH THIS: {packet.get('open_with_this', '')}",
            f"CLAIM-WARRANT-IMPACT: {packet.get('claim_warrant_impact', '')}",
            f"TOP REBUTTAL: {packet.get('top_rebuttal', '')}",
            f"JUDGE LANGUAGE: {packet.get('judge_language', '')}",
            "POWER PHRASES: " + " | ".join(f"'{phrase}'" for phrase in packet.get("power_phrases", [])),
        ]
    )


def coach_node(state: dict) -> dict:
    state["task_type"] = "debate"
    topic = topic_name(state.get("topic"))
    topic_info = state.get("topic_info", {}) or {}
    summaries = state.get("summaries", [])[:MAX_SUMMARIES]
    lead_title = str((state.get("lead_case") or {}).get("title", "")).strip()
    query = _build_debate_query(topic, topic_info, summaries, state.get("arguments", {}))
    if lead_title:
        query = f"{query} {lead_title}".strip()
    bundle = retrieve_bundle_for_node("coach_node", query, state=state)
    rag_chunks = bundle["chunks"]
    rag_context = format_retrieved_context(rag_chunks)
    state.setdefault("retrieval_plans", {})["coach_node"] = bundle["plan"] or {}
    state.setdefault("retrieval_traces", {})["coach_node"] = bundle["trace"]

    default_packet = _heuristic_debate_packet(
        topic,
        state.get("arguments", {}),
        summaries,
        topic_info,
    )
    default_coaching = _packet_to_block(default_packet)

    if not summaries and not rag_context:
        state["debate_packet"] = default_packet
        state["debate_angle"] = default_coaching
        return state

    prompt = (
        "You are a debate coach writing in the user's preferred debate style.\n"
        "Return JSON only with these keys:\n"
        "unique_angle, value_clash, burden_of_proof, mechanism, open_with_this, claim_warrant_impact, top_rebuttal, judge_language, power_phrases.\n"
        "power_phrases must be an array of 3 to 5 short lines.\n"
        "Think like a WUDC matter file writer: explain the value clash, the mechanism, the judge comparison, and how to answer the strongest opposition push.\n\n"
        f"Topic: {topic}\n"
        f"Lead case: {lead_title}\n"
        f"Summaries: {summaries}\n"
        f"Arguments: {state.get('arguments', {})}\n"
        f"Topic info: {topic_info}\n"
        f"Style RAG context: {rag_context[:MAX_RAG_CHARS]}"
    )

    try:
        llm = get_llm_with_fallback(state)
        response = cached_invoke(llm, prompt, scope="coach")
        content = str(getattr(response, "content", response)).strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content)
        packet = {
            "unique_angle": str(parsed.get("unique_angle") or default_packet["unique_angle"]).strip(),
            "value_clash": str(parsed.get("value_clash") or default_packet["value_clash"]).strip(),
            "burden_of_proof": str(parsed.get("burden_of_proof") or default_packet["burden_of_proof"]).strip(),
            "mechanism": str(parsed.get("mechanism") or default_packet["mechanism"]).strip(),
            "open_with_this": str(parsed.get("open_with_this") or default_packet["open_with_this"]).strip(),
            "claim_warrant_impact": str(parsed.get("claim_warrant_impact") or default_packet["claim_warrant_impact"]).strip(),
            "top_rebuttal": str(parsed.get("top_rebuttal") or default_packet["top_rebuttal"]).strip(),
            "judge_language": str(parsed.get("judge_language") or default_packet["judge_language"]).strip(),
            "power_phrases": parsed.get("power_phrases") if isinstance(parsed.get("power_phrases"), list) else default_packet["power_phrases"],
        }
        state["debate_packet"] = packet
        state["debate_angle"] = _packet_to_block(packet)
    except Exception:
        state["debate_packet"] = default_packet
        state["debate_angle"] = default_coaching

    return state
