from __future__ import annotations

from collections import Counter

from core.topic_utils import topic_name


def _classify_motion(motion: str) -> str:
    lowered = motion.lower()
    if lowered.startswith("thr") or "regret" in lowered:
        return "value"
    if any(token in lowered for token in ("would", "should", "abolish", "implement", "allow", "condition", "recognise", "decriminalise")):
        return "policy"
    if any(token in lowered for token in ("government", "state", "un", "court", "institution", "party", "university")):
        return "actor-based"
    return "comparative"


def _topic_info_list(topic_info: dict, key: str, limit: int = 4) -> list[str]:
    values = topic_info.get(key, []) if isinstance(topic_info, dict) else []
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()][:limit]


def motion_intelligence_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    topic_info = state.get("topic_info", {}) or {}
    motion_set = state.get("topic_motion_set", {}) or {}
    motions = [str(item).strip() for item in motion_set.get("motions_cleaned", []) if str(item).strip()]

    type_counts = Counter(_classify_motion(motion) for motion in motions)
    common_framings = []
    if any("fairness" in motion.lower() or "rights" in motion.lower() for motion in motions):
        common_framings.append("fairness and access")
    if any("stability" in motion.lower() or "order" in motion.lower() for motion in motions):
        common_framings.append("stability and order")
    if any("institution" in motion.lower() or "reform" in motion.lower() for motion in motions):
        common_framings.append("institutional design and reform")
    if any("legitim" in motion.lower() for motion in motions):
        common_framings.append("legitimacy and consent")
    if not common_framings:
        common_framings.append(f"how {topic} should be framed in competitive debate")

    prop_burdens = [
        "show why the principle or intervention solves a real structural problem",
        "justify the actor choice and explain why implementation is plausible",
    ]
    opp_burdens = [
        "show where incentives, backlash, or institutional limits break the model",
        "prove that the comparative world is safer, fairer, or more durable",
    ]

    live_cases = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 3)
    clashes = []
    for pair in (("fairness", "feasibility"), ("rights", "stability"), ("representation", "efficiency"), ("principle", "implementation")):
        if any(pair[0] in motion.lower() or pair[1] in motion.lower() for motion in motions):
            clashes.append(f"{pair[0]} vs {pair[1]}")
    if not clashes:
        clashes = ["principle vs implementation", "fairness vs feasibility"]

    motion_types = [name for name, _count in type_counts.most_common()] or ["policy"]
    state["motion_intelligence"] = {
        "topic": topic,
        "motion_types": motion_types,
        "common_framings": common_framings[:4],
        "prop_burdens": prop_burdens,
        "opp_burdens": opp_burdens,
        "common_clashes": clashes[:4],
        "balance_patterns": [
            "good motions narrow the actor and the mechanism",
            "balanced motions let both teams contest implementation and precedent",
            "bad motions become moral slogans without a comparative world",
        ],
        "drafting_guidance": {
            "preferred_scope": "clear actor, bounded mechanism, and a live conflict",
            "avoid_patterns": ["too broad", "headline-only framing", "one-sided moral wording"],
        },
        "sample_motions": motions[:6],
        "live_case_lenses": live_cases,
    }
    return state
