import json

from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from rag.evidence_organizer import format_structured_evidence, organize_evidence
from rag.retrieval_pipeline import format_retrieved_context, retrieve_bundle_for_node


MAX_RAG_CHARS = 900
MAX_SUMMARIES = 2


def _topic_info_list(topic_info: dict, key: str, limit: int = 2) -> list[str]:
    values = topic_info.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()][:limit]


def _build_debate_query(topic: str, topic_info: dict, summaries: list[str], arguments: dict, drafted_motion: dict | None = None) -> str:
    live_case = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 1)
    frameworks = _topic_info_list(topic_info, "essential_theoretical_frameworks", 2)
    concepts = _topic_info_list(topic_info, "key_concepts_own_these_precisely", 2)
    recurring = _topic_info_list(topic_info, "recurring_motions_at_wudc_level", 1)
    drafted_motion = drafted_motion or {}
    motion_text = str(drafted_motion.get("drafted_motion", "")).strip()
    pieces = [
        topic,
        "value clash burden of proof mechanism rebuttal weighing WUDC matter file",
        summaries[0] if summaries else "",
        arguments.get("middle", ""),
        live_case[0] if live_case else "",
        " | ".join(frameworks),
        " | ".join(concepts),
        recurring[0] if recurring else "",
        motion_text,
    ]
    return " ".join(piece for piece in pieces if piece).strip()


def _heuristic_debate_packet(topic: str, arguments: dict, summaries: list[str], topic_info: dict | None = None, drafted_motion: dict | None = None) -> dict:
    topic_info = topic_info or {}
    drafted_motion = drafted_motion or {}
    frameworks = _topic_info_list(topic_info, "essential_theoretical_frameworks", 1)
    concepts = _topic_info_list(topic_info, "key_concepts_own_these_precisely", 2)
    missed_angles = _topic_info_list(topic_info, "argument_angles_most_debaters_miss", 1)
    live_cases = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 1)
    recurring = _topic_info_list(topic_info, "recurring_motions_at_wudc_level", 1)
    mechanisms = _topic_info_list(topic_info, "the_mechanisms_to_understand", 2)
    motion_text = str(drafted_motion.get("drafted_motion", "")).strip()
    prop_burdens = drafted_motion.get("prop_burden", []) if isinstance(drafted_motion, dict) else []
    opp_burdens = drafted_motion.get("opp_burden", []) if isinstance(drafted_motion, dict) else []
    clash_axes = drafted_motion.get("likely_clash_axis", []) if isinstance(drafted_motion, dict) else []
    opening = arguments.get("for", [f"{topic.title()} is best opened through a fairness frame."])[0]
    rebuttal_target = arguments.get("against", ["Challenge the biggest tradeoff claim."])[0]
    summary_anchor = summaries[0].splitlines()[0].lstrip("- ").strip() if summaries else f"Anchor your framing on the biggest practical consequence in {topic}."

    unique_angle = (
        missed_angles[0]
        if missed_angles
        else (f"Frame the round around the generated motion '{motion_text}' and win the comparison on incentives, legitimacy, and reversibility." if motion_text else f"Frame {topic} as a clash between principle and implementation, then win on whichever side has better long-term incentives.")
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
        "value_clash": clash_axes[0] if clash_axes else (f"The deepest clash is between {concepts[0] if concepts else 'legitimacy'} and {concepts[1] if len(concepts) > 1 else 'order'}." if concepts else f"The deepest clash is between principle and implementation in {topic}."),
        "burden_of_proof": prop_burdens[0] if prop_burdens else "Your burden is to prove not just that the principle sounds attractive, but that the mechanism survives contact with power, incentives, and precedent.",
        "mechanism": mechanisms[0] if mechanisms else "Track who has incentives to defect, who enforces the norm, and why that enforcement sticks.",
        "open_with_this": (f"Start by defining the motion: {motion_text}. Then explain why the real clash is {clash_axes[0] if clash_axes else 'principle versus implementation'}." if motion_text else opening_line),
        "claim_warrant_impact": claim_block,
        "top_rebuttal": (f"If they dodge the motion wording, drag them back to the burden: {opp_burdens[0]}" if opp_burdens else rebuttal),
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


def _article_examples(state: dict) -> list[str]:
    lead_case = state.get("lead_case", {}) or {}
    article_context = state.get("article_context", {}) or {}
    examples: list[str] = []
    for value in (lead_case.get("title", ""), lead_case.get("content", "")):
        clean = " ".join(str(value).split()).strip()
        if clean:
            examples.append(clean[:220])
    for item in (article_context.get("notes", []) if isinstance(article_context, dict) else [])[:3]:
        clean = " ".join(str(item).split()).strip()
        if clean and clean not in examples:
            examples.append(clean[:220])
    return examples[:4]


def _teaching_block(argument: str, side: str, index: int, drafted_motion: dict, packet: dict, examples: list[str]) -> dict:
    motion_text = str(drafted_motion.get("drafted_motion", "")).strip()
    prop_burden = (drafted_motion.get("prop_burden", []) or [""])[0]
    opp_burden = (drafted_motion.get("opp_burden", []) or [""])[0]
    example = examples[min(index, len(examples) - 1)] if examples else "Use the strongest article detail to prove the mechanism."

    if side == "for":
        explanation = (
            f"This is the proposition case under the motion '{motion_text}'. You are not merely praising the principle; you must show why this world solves a real structural problem better than the status quo."
            if motion_text else
            "This is the proposition case. You must show why your world creates a better long-term outcome, not just a nicer slogan."
        )
        mechanism = prop_burden or "Track the actor, the incentive change, and the downstream benefit step by step."
        pushback = "Opposition will say your model is too idealistic, too costly, or too hard to implement consistently."
        rebuttal = f"Answer by narrowing the mechanism: show why {example} demonstrates that the status quo already imposes costs, so action is not risk-free in the first place."
    else:
        explanation = (
            f"This is the opposition case against the motion '{motion_text}'. Your job is to show where the promised gains break once real incentives, backlash, or institutional limits appear."
            if motion_text else
            "This is the opposition case. Your job is to show where the promised benefits collapse in practice."
        )
        mechanism = opp_burden or "Interrogate compliance, incentives, and second-order effects rather than accepting the framing on trust."
        pushback = "Proposition will say the principle is too important to reject just because implementation is imperfect."
        rebuttal = f"Answer that judges compare worlds, not slogans: use {example} to show why bad implementation changes who bears harm first and why that matters more."

    return {
        "claim": argument,
        "explanation": explanation,
        "mechanism": mechanism,
        "why_it_matters": "This matters because rounds are won by proving comparative impact, reversibility of harm, and who carries the burden in the real world.",
        "article_example": example,
        "likely_pushback": pushback,
        "rebuttal": rebuttal,
    }


def _build_debate_teaching(state: dict, packet: dict, drafted_motion: dict) -> dict:
    arguments = state.get("arguments", {}) or {}
    examples = _article_examples(state)
    for_blocks = [_teaching_block(argument, "for", index, drafted_motion, packet, examples) for index, argument in enumerate((arguments.get("for") or [])[:3])]
    against_blocks = [_teaching_block(argument, "against", index, drafted_motion, packet, examples) for index, argument in enumerate((arguments.get("against") or [])[:3])]

    motion_text = str(drafted_motion.get("drafted_motion", "")).strip()
    clash_axes = drafted_motion.get("likely_clash_axis", []) or []
    return {
        "motion_explanation": (
            f"The motion is asking you to debate whether the live case should be judged through the lens of '{clash_axes[0]}' and whether the proposed actor should carry that burden."
            if motion_text and clash_axes else
            f"The motion '{motion_text}' asks what standard should decide the round and who must justify the cost of acting."
            if motion_text else
            "The round is about what standard should decide the conflict and who must justify the cost of acting."
        ),
        "prop_burden": drafted_motion.get("prop_burden", []) or [packet.get("burden_of_proof", "")],
        "opp_burden": drafted_motion.get("opp_burden", []) or ["Show why the comparative world is safer or more realistic."],
        "for_arguments": for_blocks,
        "against_arguments": against_blocks,
        "core_clash": {
            "what_the_round_is_really_about": clash_axes[0] if clash_axes else packet.get("value_clash", "principle versus implementation"),
            "what_prop_must_win": (drafted_motion.get("prop_burden", []) or [packet.get("burden_of_proof", "")])[0],
            "what_opp_must_win": (drafted_motion.get("opp_burden", []) or [packet.get("top_rebuttal", "")])[0],
        },
        "mechanism": {"step_by_step_logic": [packet.get("mechanism", ""), "Show the actor, the incentive change, the immediate effect, and the long-term consequence."]},
        "framing": {
            "prop_frame": packet.get("open_with_this", ""),
            "opp_frame": packet.get("top_rebuttal", ""),
            "strategic_note": packet.get("judge_language", ""),
        },
        "rebuttal_drills": [
            {
                "if_they_say": for_blocks[0]["likely_pushback"] if for_blocks else "They claim the principle is obviously good.",
                "answer_with": against_blocks[0]["rebuttal"] if against_blocks else packet.get("top_rebuttal", ""),
                "why_that_answer_works": "It drags the round back from slogans to mechanism, comparative burden, and concrete article evidence.",
            }
        ],
        "coach_note": packet.get("unique_angle", ""),
    }


def coach_node(state: dict) -> dict:
    state["task_type"] = "debate"
    topic = topic_name(state.get("topic"))
    topic_info = state.get("topic_info", {}) or {}
    summaries = state.get("summaries", [])[:MAX_SUMMARIES]
    lead_title = str((state.get("lead_case") or {}).get("title", "")).strip()
    drafted_motion = state.get("drafted_motion", {}) or {}
    query = _build_debate_query(topic, topic_info, summaries, state.get("arguments", {}), drafted_motion)
    if lead_title:
        query = f"{query} {lead_title}".strip()
    bundle = retrieve_bundle_for_node("coach_node", query, state=state)
    rag_chunks = bundle["chunks"]
    rag_context = format_retrieved_context(rag_chunks)
    structured_evidence = organize_evidence(rag_chunks)
    structured_context = format_structured_evidence(structured_evidence, per_section=2)
    state.setdefault("retrieval_plans", {})["coach_node"] = bundle["plan"] or {}
    state.setdefault("retrieval_traces", {})["coach_node"] = bundle["trace"]
    state["coach_evidence"] = structured_evidence

    default_packet = _heuristic_debate_packet(topic, state.get("arguments", {}), summaries, topic_info, drafted_motion)
    default_coaching = _packet_to_block(default_packet)

    if not summaries and not rag_context:
        state["debate_packet"] = default_packet
        state["debate_angle"] = default_coaching
        state["debate_teaching"] = _build_debate_teaching(state, default_packet, drafted_motion)
        return state

    prompt = (
        "You are a debate coach writing in the user's preferred debate style.\n"
        "Return JSON only with these keys:\n"
        "unique_angle, value_clash, burden_of_proof, mechanism, open_with_this, claim_warrant_impact, top_rebuttal, judge_language, power_phrases.\n"
        "power_phrases must be an array of 3 to 5 short lines.\n"
        "Think like a WUDC matter file writer: explain the value clash, the mechanism, the judge comparison, and how to answer the strongest opposition push.\n\n"
        f"Topic: {topic}\n"
        f"Lead case: {lead_title}\n"
        f"Generated motion: {drafted_motion.get('drafted_motion', '')}\n"
        f"Summaries: {summaries}\n"
        f"Arguments: {state.get('arguments', {})}\n"
        f"Topic info: {topic_info}\n"
        f"Structured evidence:\n{structured_context[:MAX_RAG_CHARS]}\n\n"
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
        state["debate_teaching"] = _build_debate_teaching(state, packet, drafted_motion)
    except Exception:
        state["debate_packet"] = default_packet
        state["debate_angle"] = default_coaching
        state["debate_teaching"] = _build_debate_teaching(state, default_packet, drafted_motion)

    return state
