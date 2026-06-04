from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node


def rag_enrich_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    chunks = retrieve_for_node("rag_enrich_node", topic)
    rag_context = format_retrieved_context(chunks)
    reference_background = str(state.get("reference_background", "")).strip()
    if reference_background and rag_context:
        state["enriched_context"] = f"WIKIPEDIA BACKGROUND:\n{reference_background}\n\n{rag_context}"
    else:
        state["enriched_context"] = reference_background or rag_context
    return state
