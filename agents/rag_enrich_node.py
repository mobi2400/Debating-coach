from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_bundle_for_node


def rag_enrich_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    bundle = retrieve_bundle_for_node("rag_enrich_node", topic, state=state)
    chunks = bundle["chunks"]
    rag_context = format_retrieved_context(chunks)
    state.setdefault("retrieval_plans", {})["rag_enrich_node"] = bundle["plan"] or {}
    state.setdefault("retrieval_traces", {})["rag_enrich_node"] = bundle["trace"]
    reference_background = str(state.get("reference_background", "")).strip()
    if reference_background and rag_context:
        state["enriched_context"] = f"WIKIPEDIA BACKGROUND:\n{reference_background}\n\n{rag_context}"
    else:
        state["enriched_context"] = reference_background or rag_context
    return state
