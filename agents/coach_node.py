import json

from core.debate_guidance import build_targeted_context
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






def _extract_json_object(content: str) -> dict | None:
    text = str(content or '').strip()
    if not text:
        return None
    if text.startswith('```'):
        text = text.split('```', 2)[1]
        if text.startswith('json'):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        snippet = text[start:end + 1]
        try:
            parsed = json.loads(snippet)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _heuristic_framing_example(argument: str, framing: str) -> str:
    lower = argument.lower()
    if 'access' in lower or 'representation' in lower:
        return 'Say: this round is not about abstract sympathy; it is about whether excluded groups gain real entry into the institutions that write the rules.'
    if 'network' in lower or 'elite' in lower or 'pipeline' in lower:
        return 'Say: the real issue is not one biased decision but a structure that keeps reproducing the same people in power.'
    if 'poverty' in lower or 'violence' in lower or 'health' in lower:
        return 'Say: judge this as a long-term social-investment question, not a short-term budget question.'
    if 'symbolic' in lower or 'optics' in lower:
        return 'Say: the question is whether the reform changes lived outcomes or just improves the optics of the institution.'
    if 'backlash' in lower or 'compliance' in lower:
        return 'Say: what matters is not whether the goal sounds noble, but whether the tool keeps enough legitimacy to survive real resistance.'
    return f'Say: {framing}'


def _heuristic_mechanism_example(argument: str, mechanism: str) -> str:
    lower = argument.lower()
    if 'access' in lower or 'representation' in lower:
        return 'Example chain: more women enter leadership -> they influence rules and priorities -> bias is challenged internally -> protections become harder to reverse.'
    if 'network' in lower or 'elite' in lower or 'pipeline' in lower:
        return 'Example chain: change who gets selected at the top -> mentoring and promotion norms shift -> the next tier of leaders becomes more diverse.'
    if 'poverty' in lower or 'violence' in lower or 'health' in lower:
        return 'Example chain: invest in legal and social protection -> immediate exposure to harm falls -> long-term education and earning outcomes improve -> poverty cycles weaken.'
    if 'symbolic' in lower or 'optics' in lower:
        return 'Example chain: the institution hits the visible target -> public pressure drops -> deeper reforms in pay, safety, and retention are postponed.'
    if 'backlash' in lower or 'compliance' in lower:
        return 'Example chain: stakeholders see the reform as imposed -> resentment rises -> compliance weakens -> the policy loses staying power.'
    return f'Example chain: {mechanism}'


def _enrich_argument_blocks_with_llm(state: dict, drafted_motion: dict, blocks: list[dict], side: str, guidance: str) -> list[dict]:
    if not blocks:
        return blocks

    topic = topic_name(state.get("topic"))
    lead_case = state.get("lead_case", {}) or {}
    lead_title = str(lead_case.get("title", "")).strip()
    motion_text = str(drafted_motion.get("drafted_motion", "")).strip()
    payload = []
    for block in blocks[:2]:
        payload.append({
            "claim": block.get("claim", ""),
            "article_example": block.get("article_example", ""),
            "existing_framing": block.get("explanation", ""),
            "existing_mechanism": block.get("mechanism", ""),
        })

    prompt = (
        "You are refining debate teaching blocks for a student.\n"
        "Return JSON only with one key: blocks.\n"
        "blocks must be an array with the same number of items as the input.\n"
        "For each item return these keys exactly: claim, framing, framing_example, mechanism, mechanism_example.\n"
        "framing must explain what this argument is really about in the round.\n"
        "framing_example must be one actual line the student could say in a speech to frame this argument.\n"
        "mechanism must explain how this exact argument works step by step.\n"
        "mechanism_example must be one concrete example chain showing that mechanism in action.\n"
        "Do not repeat the same framing or mechanism across different arguments unless the claims are genuinely identical.\n"
        "Be specific to each claim.\n\n"
        f"DEBATE GUIDANCE:\n{guidance}\n\n"
        f"Topic: {topic}\n"
        f"Lead case: {lead_title}\n"
        f"Motion: {motion_text}\n"
        f"Side: {side}\n"
        f"INPUT BLOCKS: {json.dumps(payload, ensure_ascii=False)}"
    )

    llm = get_llm_with_fallback(state)
    response = cached_invoke(llm, prompt, scope=f"coach_{side}_blocks")
    parsed = _extract_json_object(str(getattr(response, 'content', response)))
    items = parsed.get('blocks') if isinstance(parsed, dict) else None
    if not isinstance(items, list):
        raise ValueError('coach block enrichment returned invalid JSON')

    enriched: list[dict] = []
    for base, item in zip(blocks, items):
        enriched.append({
            **base,
            "claim": str(item.get("claim") or base.get("claim", "")).strip(),
            "explanation": str(item.get("framing") or base.get("explanation", "")).strip(),
            "framing_example": str(item.get("framing_example") or _heuristic_framing_example(base.get("claim", ""), base.get("explanation", ""))).strip(),
            "mechanism": str(item.get("mechanism") or base.get("mechanism", "")).strip(),
            "mechanism_example": str(item.get("mechanism_example") or _heuristic_mechanism_example(base.get("claim", ""), base.get("mechanism", ""))).strip(),
        })

    while len(enriched) < len(blocks):
        base = blocks[len(enriched)]
        enriched.append({
            **base,
            "framing_example": _heuristic_framing_example(base.get("claim", ""), base.get("explanation", "")),
            "mechanism_example": _heuristic_mechanism_example(base.get("claim", ""), base.get("mechanism", "")),
        })
    return enriched

def _build_clash_block(packet: dict, drafted_motion: dict, topic: str) -> dict:
    clash_axes = drafted_motion.get("likely_clash_axis", []) or []
    prop_burdens = drafted_motion.get("prop_burden", []) or [packet.get("burden_of_proof", "")]
    opp_burdens = drafted_motion.get("opp_burden", []) or [packet.get("top_rebuttal", "")]
    main_clash = clash_axes[0] if clash_axes else packet.get("value_clash", f"principle versus implementation in {topic}")
    what_prop = prop_burdens[0] if prop_burdens else packet.get("burden_of_proof", "")
    what_opp = opp_burdens[0] if opp_burdens else packet.get("top_rebuttal", "")
    judge = packet.get("judge_language", "Tell the judge why your world is more likely, more stable, and less reversible in its harms.")
    return {
        "main_clash": str(main_clash).strip(),
        "what_prop_says": str(what_prop).strip(),
        "what_opp_says": str(what_opp).strip(),
        "judge_comparison": str(judge).strip(),
    }


def _build_coach_note_block(packet: dict, drafted_motion: dict, topic: str) -> dict:
    unique_angle = str(packet.get("unique_angle", "")).strip()
    open_with = str(packet.get("open_with_this", "")).strip()
    rebuttal = str(packet.get("top_rebuttal", "")).strip()
    judge = str(packet.get("judge_language", "")).strip()
    hidden = unique_angle or f"The hidden lens in {topic} is usually whether the mechanism survives real incentives, not whether the slogan sounds attractive."
    miss = rebuttal or "Most debaters state the value but never prove the actor chain, the incentive shift, and the comparative impact."
    opening = open_with or f"Open by telling the judge what question actually decides the round in {topic}, then show why your side answers it better."
    wins = judge or "Tell the judge why your world is more likely, more stable, and less reversible in its harms."
    return {
        "hidden_lens": hidden,
        "what_most_debaters_miss": miss,
        "how_to_open": opening,
        "what_wins_the_judge": wins,
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


def _argument_framing(argument: str, side: str, example: str) -> str:
    lower = argument.lower()
    if side == "for":
        if any(token in lower for token in ("rights", "equal", "access", "representation", "voice")):
            return "Frame this as an access-and-legitimacy argument: the judge should care whether excluded groups gain real entry into institutions that shape rules, status, and opportunity."
        if any(token in lower for token in ("network", "elite", "pipeline", "promotion", "hiring")):
            return "Frame this as a structural-reproduction argument: the issue is not one bad decision but a system that keeps rewarding the same people again and again."
        if any(token in lower for token in ("backlash", "delay", "speed", "reform", "voluntary")):
            return "Frame this as an urgency argument: delaying reform is not neutral if the current arrangement keeps allocating harm and exclusion every year."
        return "Frame this as a structural reform argument: the judge should care whether the policy changes who gets access, voice, and institutional power over time."

    if any(token in lower for token in ("symbolic", "perform", "legitimacy", "shortcut", "optics")):
        return "Frame this as a symbolic-versus-material change argument: the judge should care whether the reform actually changes lived outcomes or merely improves the institution's image."
    if any(token in lower for token in ("backlash", "coerc", "resent", "trust", "compliance")):
        return "Frame this as a backlash and compliance argument: the key question is whether the policy triggers resistance that weakens the very goal it claims to advance."
    if any(token in lower for token in ("pipeline", "care", "labour", "deeper", "structural")):
        return "Frame this as a misdiagnosis argument: the judge should care whether the reform targets the visible symptom while leaving the deeper engine of exclusion intact."
    return "Frame this as a comparative-harm argument: the judge should care where the model misfires, who pays first, and whether the same goal can be reached with less damage."


def _argument_mechanism(argument: str, side: str, example: str, fallback: str) -> str:
    lower = argument.lower()
    if side == "for":
        if any(token in lower for token in ("network", "elite", "pipeline", "promotion", "hiring")):
            return "Explain the chain clearly: the reform changes who gets selected at the top, that reshapes mentoring and promotion incentives below, and over time the institution stops reproducing the same elite profile."
        if any(token in lower for token in ("rights", "equal", "access", "representation", "voice")):
            return "Explain the chain clearly: once excluded groups gain formal access and representation, they can influence rules, challenge bias inside the institution, and secure more durable protections for those below them."
        if any(token in lower for token in ("delay", "speed", "reform", "voluntary", "market")):
            return "Explain the chain clearly: a binding reform forces immediate behavioural change, while voluntary change lets current gatekeepers postpone adjustment and preserve the old distribution of power."
        return "Explain the actor, the institutional change, and the downstream effect: who changes behaviour first, what incentive shifts, and why that produces better long-term outcomes."

    if any(token in lower for token in ("symbolic", "perform", "optics", "shortcut")):
        return "Explain the chain clearly: the institution hits the visible metric, claims progress, and then loses pressure to fix the harder causes of exclusion in pay, care burdens, retention, or workplace culture."
    if any(token in lower for token in ("backlash", "coerc", "resent", "trust", "compliance")):
        return "Explain the chain clearly: once people see the reform as imposed rather than earned, compliance becomes thinner, resentment grows, and the policy loses both legitimacy and staying power."
    if any(token in lower for token in ("pipeline", "care", "labour", "deeper", "structural")):
        return "Explain the chain clearly: the reform acts at the endpoint, but the real exclusion happens earlier through schooling, care work, hiring filters, and retention, so the core inequality survives."
    return fallback or "Show exactly where the mechanism breaks in practice: who resists, who bears the cost first, and why the promised benefit fails to materialise at scale."


def _teaching_block_seed(argument: str, side: str, index: int, drafted_motion: dict, packet: dict, examples: list[str]) -> dict:
    prop_burden = (drafted_motion.get("prop_burden", []) or [""])[0]
    opp_burden = (drafted_motion.get("opp_burden", []) or [""])[0]
    example = examples[min(index, len(examples) - 1)] if examples else "Use the strongest article detail to prove the mechanism."

    if side == "for":
        explanation = _argument_framing(argument, side, example)
        mechanism = _argument_mechanism(argument, side, example, prop_burden)
        pushback = "Opposition will say your model is too idealistic, too costly, or too hard to implement consistently."
        rebuttal = f"Answer by narrowing the mechanism: show why {example} demonstrates that the status quo already imposes costs, so action is not risk-free in the first place."
    else:
        explanation = _argument_framing(argument, side, example)
        mechanism = _argument_mechanism(argument, side, example, opp_burden)
        pushback = "Proposition will say the principle is too important to reject just because implementation is imperfect."
        rebuttal = f"Answer that judges compare worlds, not slogans: use {example} to show why bad implementation changes who bears harm first and why that matters more."

    return {
        "claim": argument,
        "explanation": explanation,
        "framing_example": _heuristic_framing_example(argument, explanation),
        "mechanism": mechanism,
        "mechanism_example": _heuristic_mechanism_example(argument, mechanism),
        "why_it_matters": "This matters because rounds are won by proving comparative impact, reversibility of harm, and who carries the burden in the real world.",
        "article_example": example,
        "likely_pushback": pushback,
        "rebuttal": rebuttal,
    }


def _teaching_block(state: dict | None, argument: str, side: str, index: int, drafted_motion: dict, packet: dict, examples: list[str]) -> dict:
    base = _teaching_block_seed(argument, side, index, drafted_motion, packet, examples)
    if not state:
        return base

    guidance = build_targeted_context(
        'coach_node',
        sections=[
            ('concepts', 'argumentation'),
            ('concepts', 'framing'),
            ('concepts', 'mechanism'),
            ('contract', 'shared_definitions.argument_block'),
            ('contract', 'nodes.coach_node'),
        ],
        max_chars=2400,
    )
    try:
        enriched = _enrich_argument_blocks_with_llm(state, drafted_motion, [base], 'proposition' if side == 'for' else 'opposition', guidance)
        return enriched[0] if enriched else base
    except Exception:
        return base


def _build_debate_teaching(state: dict, packet: dict, drafted_motion: dict) -> dict:
    arguments = state.get("arguments", {}) or {}
    examples = _article_examples(state)
    for_blocks = [_teaching_block(state, argument, "for", index, drafted_motion, packet, examples) for index, argument in enumerate((arguments.get("for") or [])[:2])]
    against_blocks = [_teaching_block(state, argument, "against", index, drafted_motion, packet, examples) for index, argument in enumerate((arguments.get("against") or [])[:2])]

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
        "core_clash": _build_clash_block(packet, drafted_motion, topic_name(state.get("topic"))),
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
        "coach_note": _build_coach_note_block(packet, drafted_motion, topic_name(state.get("topic"))),
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

    guidance = build_targeted_context(
        'coach_node',
        sections=[
            ('concepts', 'framing'),
            ('concepts', 'mechanism'),
            ('concepts', 'clash'),
            ('concepts', 'rebuttal'),
            ('concepts', 'coach_notes'),
            ('contract', 'shared_definitions.argument_block'),
            ('contract', 'shared_definitions.clash_block'),
            ('contract', 'shared_definitions.coach_note_block'),
            ('contract', 'nodes.coach_node'),
            ('contract', 'cross_node_guardrails'),
        ],
        max_chars=3200,
    )

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
