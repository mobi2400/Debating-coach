from __future__ import annotations

from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_bundle_for_node
from tools.wiki_tool import wiki_search


def _background_sentences(text: str, limit: int = 3) -> list[str]:
    parts: list[str] = []
    for raw in str(text).replace("\n", " ").split(". "):
        sentence = " ".join(raw.split()).strip(" -")
        if sentence:
            parts.append(sentence.rstrip(".") + ".")
        if len(parts) >= limit:
            break
    return parts


def preknowledge_enrichment_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    lead_case = state.get("lead_case", {}) or {}
    lead_title = str(lead_case.get("title", "")).strip()
    query = lead_title or topic

    wiki = wiki_search(query)
    reference_background = str(wiki.get("content", "")).strip() if isinstance(wiki, dict) else ""
    if not reference_background:
        reference_background = str(state.get("reference_background", "")).strip()

    rag_query = f"{topic} prerequisites concepts framework {lead_title}".strip()
    bundle = retrieve_bundle_for_node("rag_enrich_node", rag_query, state=state)
    rag_chunks = bundle["chunks"]
    rag_context = format_retrieved_context(rag_chunks)
    state.setdefault("retrieval_plans", {})["preknowledge_enrichment_node"] = bundle["plan"] or {}
    state.setdefault("retrieval_traces", {})["preknowledge_enrichment_node"] = bundle["trace"]

    state["reference_background"] = reference_background[:2000]
    state["enriched_context"] = rag_context
    state["preknowledge_notes"] = _background_sentences(reference_background, limit=3)
    return state
