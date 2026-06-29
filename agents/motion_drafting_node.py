from __future__ import annotations

from core.topic_utils import topic_name


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
    actor = _actor_for_topic(topic)

    recurring = _topic_info_list(topic_info, "recurring_motions_at_wudc_level", 1)
    live_cases = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 1)
    case_label = lead_title.split("?", 1)[0].split(":", 1)[0].strip() or lead_title
    clash_axis = common_clashes[0]
    framing = common_framings[0]
    motion_type = motion_types[0]

    if motion_type == "value":
        drafted_motion = f"THBT responses to {case_label} should be judged primarily through {clash_axis}"
    elif motion_type == "actor-based":
        drafted_motion = f"THW have {actor} prioritise {framing} when responding to {case_label}"
    else:
        drafted_motion = f"THBT {actor} should prioritise {framing} over short-term expediency in responding to {case_label}"

    prop_burden = [
        f"prove that {drafted_motion[5:] if drafted_motion.startswith('THBT ') else drafted_motion} solves a real problem rather than just sounding principled",
        "show why the chosen actor can implement the response credibly and why the benefits outweigh the tradeoffs",
    ]
    opp_burden = [
        "show where the mechanism breaks in practice or why the comparative world avoids the same harm at lower cost",
        "contest the framing by proving that the neglected side of the clash matters more in this live case",
    ]

    state["drafted_motion"] = {
        "drafted_motion": drafted_motion,
        "motion_type": motion_type,
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
