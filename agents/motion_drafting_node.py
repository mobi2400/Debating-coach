from __future__ import annotations

import random

from core.debate_guidance import get_node_guidance
from core.topic_utils import topic_name


def _clean_case_label(title: str, fallback_topic: str) -> str:
    raw = str(title or "").strip()
    if not raw:
        return f"today's {fallback_topic} case"

    for separator in ("|", " - ", " ? "):
        if separator in raw:
            raw = raw.split(separator, 1)[0].strip()

    raw = raw.split("?", 1)[0].split(":", 1)[0].strip() or raw
    words = raw.split()
    if len(words) > 10:
        raw = " ".join(words[:10]).strip()
    return raw




def _guidance_list(guidance: dict, path: str) -> list[str]:
    value = ((guidance.get("contract") or {}).get(path) or (guidance.get("concepts") or {}).get(path) or [])
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _select_motion_type(topic: str, motion_types: list[str], balance_signals: list[str], contract_rules: list[str]) -> str:
    candidates = [str(item).strip().lower() for item in motion_types if str(item).strip()]
    if not candidates:
        return "policy"

    signals = " ".join(balance_signals + contract_rules).lower()
    weights: dict[str, float] = {candidate: 1.0 for candidate in candidates}

    if "actor-based" in weights:
        weights["actor-based"] += 1.2
    if "policy" in weights:
        weights["policy"] += 0.9
    if "comparative" in weights:
        weights["comparative"] += 0.7
    if "value" in weights:
        weights["value"] += 0.4

    if any(word in signals for word in ("actor", "institution", "government", "state", "capacity", "leverage", "legitimacy")):
        if "actor-based" in weights:
            weights["actor-based"] += 2.0
        if "policy" in weights:
            weights["policy"] += 0.6

    if any(word in signals for word in ("comparative", "better world", "rather than", "compared with", "alternative world")):
        if "comparative" in weights:
            weights["comparative"] += 2.0
        if "policy" in weights:
            weights["policy"] += 0.4

    if any(word in signals for word in ("regret", "house regrets", "value clash", "moral trade-off", "principled")):
        if "value" in weights:
            weights["value"] += 1.8
        if "comparative" in weights:
            weights["comparative"] += 0.3

    if any(word in signals for word in ("live case", "current case", "implementation", "stakeholder", "institutional design")):
        if "actor-based" in weights:
            weights["actor-based"] += 0.8
        if "policy" in weights:
            weights["policy"] += 0.8

    pool = list(weights.keys())
    chosen = random.choices(pool, weights=[max(weights[item], 0.1) for item in pool], k=1)[0]
    return chosen


def _select_framing(common_framings: list[str], guidance_text: str) -> str:
    for item in common_framings:
        clean = str(item).strip()
        if clean:
            return clean
    lowered = guidance_text.lower()
    if "fairness" in lowered and "access" in lowered:
        return "fairness and access"
    if "legitimacy" in lowered and "stability" in lowered:
        return "legitimacy and long-term stability"
    return "fairness and access"


def _build_burdens(motion_type: str, clash_axis: str, framing: str, guidance_text: str) -> tuple[list[str], list[str]]:
    prop = [
        "prove the proposed response solves a real structural problem rather than just sounding principled",
        "show why the chosen actor can implement the response credibly and why the benefits outweigh the tradeoffs",
    ]
    opp = [
        "show where the mechanism breaks in practice or why the comparative world avoids the same harm at lower cost",
        f"contest the framing by proving that the neglected side of '{clash_axis}' matters more in this live case",
    ]

    lowered = guidance_text.lower()
    if motion_type == "value" or "principled" in lowered:
        prop[0] = f"prove that prioritising {framing} is the right standard for judging this case, not just an attractive slogan"
        opp[0] = "show that the principle either misfires in practice or is outweighed by the competing value in this case"
    elif motion_type == "actor-based":
        prop[0] = "prove this actor is the right one to carry the burden and can change the outcome in a meaningful way"
        opp[0] = "show that this actor lacks the legitimacy, leverage, or practical capacity to deliver the promised outcome"
    return prop, opp



def _draft_motion_text(motion_type: str, actor: str, framing: str, clash_axis: str, case_label: str) -> str:
    if motion_type == "value":
        return f"THR prioritising short-term expediency over {framing} when responding to {case_label}"
    if motion_type == "actor-based":
        return f"THW have {actor} prioritise {framing} when responding to {case_label}"
    if motion_type == "comparative":
        return f"THBT it is better to resolve {case_label} through {framing} rather than short-term expediency"
    return f"THW have {actor} prioritise {framing} over short-term expediency when responding to {case_label}"



def _motion_type_explanation(motion_type: str) -> dict:
    explanations = {
        "policy": {
            "what_it_means": "This is a policy/action motion. Proposition must defend a concrete course of action by a real actor, and opposition can attack either the model, the actor, or the comparative consequences.",
            "how_to_debate_it": "Build arguments around implementation, incentives, trade-offs, and what changes in the world once the policy is actually applied.",
        },
        "actor-based": {
            "what_it_means": "This is an actor-choice motion. The round is not only about whether the goal is good, but whether this actor is the right one to carry the burden and has the legitimacy and capacity to do so.",
            "how_to_debate_it": "Build arguments around actor capacity, legitimacy, leverage, and why this actor succeeds or fails compared with alternatives.",
        },
        "value": {
            "what_it_means": "This is a value/regret-style motion. The round turns more on the right standard for judging the issue than on a detailed implementation model.",
            "how_to_debate_it": "Build arguments around principles, moral trade-offs, competing values, and why one side gives the judge the better standard for evaluating the case.",
        },
        "comparative": {
            "what_it_means": "This is a comparative-world motion. The round asks which approach creates the better world, not just whether one side sounds attractive in isolation.",
            "how_to_debate_it": "Build arguments by comparing two mechanisms, two sets of harms, and which world is more durable, fair, and realistic.",
        },
    }
    return explanations.get(motion_type, {
        "what_it_means": "This motion asks the judge to compare different ways of resolving the case.",
        "how_to_debate_it": "Build arguments around burden, mechanism, and comparative impact.",
    })

def _topic_info_list(topic_info: dict, key: str, limit: int = 3) -> list[str]:
    values = topic_info.get(key, []) if isinstance(topic_info, dict) else []
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()][:limit]


def _actor_for_topic(topic: str) -> str:
    mapping = {
        "international relations": "states and international institutions",
        "geopolitics": "states and strategic alliances",
        "economics and finance": "governments and regulators",
        "feminism and gender": "governments and major public institutions",
    }
    return mapping.get(topic.lower(), "public institutions")


def motion_drafting_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    topic_info = state.get("topic_info", {}) or {}
    lead_case = state.get("lead_case", {}) or {}
    lead_title = str(lead_case.get("title", "")).strip() or f"today's {topic} case"
    motion_intelligence = state.get("motion_intelligence", {}) or {}
    common_clashes = motion_intelligence.get("common_clashes", []) or ["principle vs implementation"]
    common_framings = motion_intelligence.get("common_framings", []) or ["fairness and access"]
    motion_types = motion_intelligence.get("motion_types", []) or ["policy"]
    guidance = get_node_guidance("motion_drafting_node")
    contract_rules = _guidance_list(guidance, "nodes.motion_drafting_node.must_do")
    balance_rules = _guidance_list(guidance, "nodes.motion_drafting_node.quality_checks")
    guidance_text = " ".join(contract_rules + balance_rules)
    actor = _actor_for_topic(topic)

    recurring = _topic_info_list(topic_info, "recurring_motions_at_wudc_level", 1)
    live_cases = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 1)
    case_label = _clean_case_label(lead_title, topic)
    clash_axis = common_clashes[0]
    framing = _select_framing(common_framings, guidance_text)
    motion_type = _select_motion_type(topic, motion_types, common_clashes + balance_rules, contract_rules)

    drafted_motion = _draft_motion_text(motion_type, actor, framing, clash_axis, case_label)

    prop_burden, opp_burden = _build_burdens(motion_type, clash_axis, framing, guidance_text)

    motion_explainer = _motion_type_explanation(motion_type)

    state["drafted_motion"] = {
        "drafted_motion": drafted_motion,
        "case_label": case_label,
        "motion_type": motion_type,
        "motion_type_explanation": motion_explainer,
        "actor": actor,
        "scope": f"Use the article '{lead_title}' as the live case and keep the round focused on the institutions directly shaping it.",
        "prop_burden": prop_burden,
        "opp_burden": opp_burden,
        "likely_clash_axis": common_clashes[:3],
        "why_this_motion_is_balanced": (
            f"It uses the real case '{lead_title}' but forces both teams to contest {clash_axis}, actor choice, and implementation instead of only trading slogans."
        ),
        "inspiration": recurring[0] if recurring else (live_cases[0] if live_cases else ""),
    }
    return state
