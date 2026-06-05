import json

from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node


MAX_RAG_CHARS = 1000
MAX_SUMMARIES = 2


def _topic_info_list(topic_info: dict, key: str, limit: int = 2) -> list[str]:
    values = topic_info.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()][:limit]


def _heuristic_arguments(topic: str, summaries: list[str], rag_context: str, topic_info: dict | None = None) -> dict:
    topic_info = topic_info or {}
    first_summary = summaries[0] if summaries else f"The topic {topic} has multiple legitimate framings."
    second_summary = summaries[1] if len(summaries) > 1 else first_summary
    frameworks = _topic_info_list(topic_info, "essential_theoretical_frameworks", 2)
    mechanisms = _topic_info_list(topic_info, "the_mechanisms_to_understand", 2)
    missed_angles = _topic_info_list(topic_info, "argument_angles_most_debaters_miss", 2)
    live_cases = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 1)

    for_claim = frameworks[0] if frameworks else first_summary.splitlines()[0].lstrip("- ").strip()
    against_claim = mechanisms[0] if mechanisms else second_summary.splitlines()[0].lstrip("- ").strip()
    weighing_hint = (
        missed_angles[0]
        if missed_angles
        else (
            "Use the stored debate theory context to add warrants and weighing."
            if rag_context
            else "Support this with examples, mechanisms, and comparative impact."
        )
    )
    middle = (
        f"Use the live case '{live_cases[0]}' to accept the principle but dispute who should bear the cost, who enforces the norm, and what precedent it sets."
        if live_cases
        else f"A strong middle ground on {topic} accepts the principle but disputes scale, speed, or institutional design."
    )

    return {
        "for": [
            f"Defend {topic} by showing why this structure protects legitimacy, fairness, or long-term stability.",
            for_claim,
            weighing_hint,
        ],
        "against": [
            f"Challenge {topic} by showing where implementation, incentives, or power asymmetry breaks the ideal story.",
            against_claim,
            "Interrogate second-order effects, incentives, and unintended consequences.",
        ],
        "middle": middle,
    }


def argue_node(state: dict) -> dict:
    state["task_type"] = "argue"
    topic = topic_name(state.get("topic"))
    summaries = state.get("summaries", [])[:MAX_SUMMARIES]
    topic_info = state.get("topic_info", {}) or {}
    lead_title = str((state.get("lead_case") or {}).get("title", "")).strip()
    query = f"{topic} {lead_title}".strip()
    rag_chunks = retrieve_for_node("argue_node", query)
    rag_context = format_retrieved_context(rag_chunks)

    default_arguments = _heuristic_arguments(topic, summaries, rag_context, topic_info)

    if not summaries and not rag_context:
        state["arguments"] = default_arguments
        return state

    prompt = (
        "You are generating debate arguments.\n"
        "Return JSON only with keys: for, against, middle.\n"
        "'for' and 'against' must each be arrays of exactly 3 arguments.\n"
        "'middle' must be one nuanced bridging position.\n\n"
        f"Topic: {topic}\n"
        f"Lead case: {lead_title}\n"
        f"Summaries: {json.dumps(summaries, ensure_ascii=False)}\n"
        f"RAG context: {rag_context[:MAX_RAG_CHARS]}"
    )

    def _normalize_arg_list(value, fallback: list[str]) -> list[str]:
        if not isinstance(value, list):
            return fallback
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        if len(cleaned) >= 3:
            return cleaned[:3]
        # Pad with heuristic so we always have exactly 3 arguments per side.
        for filler in fallback:
            if filler not in cleaned:
                cleaned.append(filler)
            if len(cleaned) == 3:
                break
        return (cleaned + fallback)[:3]

    try:
        llm = get_llm_with_fallback(state)
        response = cached_invoke(llm, prompt, scope="argue")
        content = str(getattr(response, "content", response)).strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("argue LLM returned non-object JSON")

        state["arguments"] = {
            "for": _normalize_arg_list(parsed.get("for"), default_arguments["for"]),
            "against": _normalize_arg_list(parsed.get("against"), default_arguments["against"]),
            "middle": str(parsed.get("middle") or default_arguments["middle"]).strip(),
        }
    except Exception as exc:
        print(f"[Argue] LLM parse failed: {exc}")
        state["arguments"] = default_arguments

    return state
