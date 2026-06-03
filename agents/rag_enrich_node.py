from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node


def rag_enrich_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    chunks = retrieve_for_node("rag_enrich_node", topic)
    state["enriched_context"] = format_retrieved_context(chunks)
    return state
