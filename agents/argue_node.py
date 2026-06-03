import json

from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node


MAX_RAG_CHARS = 2500


def _heuristic_arguments(topic: str, summaries: list[str], rag_context: str) -> dict:
    first_summary = summaries[0] if summaries else f"The topic {topic} has multiple legitimate framings."
    second_summary = summaries[1] if len(summaries) > 1 else first_summary
    context_hint = (
        "Use the stored debate theory context to add warrants and weighing."
        if rag_context
        else "Support this with examples, mechanisms, and comparative impact."
    )

    return {
        "for": [
            f"{topic.title()} can be defended on fairness and access grounds.",
            f"{first_summary.splitlines()[0].lstrip('- ').strip()}",
            context_hint,
        ],
        "against": [
            f"{topic.title()} can be challenged on implementation cost or tradeoff grounds.",
            f"{second_summary.splitlines()[0].lstrip('- ').strip()}",
            "Interrogate second-order effects, incentives, and unintended consequences.",
        ],
        "middle": (
            f"A strong middle ground on {topic} accepts the principle but disputes scale, speed, "
            "or institutional design."
        ),
    }


def argue_node(state: dict) -> dict:
    state["task_type"] = "argue"
    topic = topic_name(state.get("topic"))
    summaries = state.get("summaries", [])
    rag_chunks = retrieve_for_node("argue_node", topic)
    rag_context = format_retrieved_context(rag_chunks)

    default_arguments = _heuristic_arguments(topic, summaries, rag_context)

    if not summaries and not rag_context:
        state["arguments"] = default_arguments
        return state

    prompt = (
        "You are generating debate arguments.\n"
        "Return JSON only with keys: for, against, middle.\n"
        "'for' and 'against' must each be arrays of exactly 3 arguments.\n"
        "'middle' must be one nuanced bridging position.\n\n"
        f"Topic: {topic}\n"
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
