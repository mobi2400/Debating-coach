from __future__ import annotations

from core.topic_utils import topic_name
from rag.evidence_organizer import format_structured_evidence, organize_evidence
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


def _topic_frameworks(topic_info: dict) -> list[str]:
    frameworks = topic_info.get("essential_theoretical_frameworks", []) if isinstance(topic_info, dict) else []
    if not isinstance(frameworks, list):
        return []
    return [str(item).strip() for item in frameworks if str(item).strip()][:3]


def _topic_concepts(topic_info: dict) -> list[str]:
    concepts = topic_info.get("key_concepts_own_these_precisely", []) if isinstance(topic_info, dict) else []
    if not isinstance(concepts, list):
        return []
    return [str(item).strip() for item in concepts if str(item).strip()][:3]


def topic_foundation_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    topic_info = state.get("topic_info", {}) or {}

    wiki = wiki_search(topic)
    reference_background = str(wiki.get("content", "")).strip() if isinstance(wiki, dict) else ""
    if not reference_background:
        reference_background = str(state.get("reference_background", "")).strip()

    rag_query = f"{topic} overview foundations concepts debate frameworks".strip()
    bundle = retrieve_bundle_for_node("topic_foundation_node", rag_query, state=state)
    rag_chunks = bundle["chunks"]
    rag_context = format_retrieved_context(rag_chunks)
    structured_evidence = organize_evidence(rag_chunks)
    structured_context = format_structured_evidence(structured_evidence, per_section=2)

    state.setdefault("retrieval_plans", {})["topic_foundation_node"] = bundle["plan"] or {}
    state.setdefault("retrieval_traces", {})["topic_foundation_node"] = bundle["trace"]

    background_notes = _background_sentences(reference_background, limit=3)
    topic_foundation = {
        "topic": topic,
        "overview": reference_background[:2000],
        "frameworks": _topic_frameworks(topic_info),
        "key_concepts": _topic_concepts(topic_info),
        "retrieved_context": rag_context,
        "structured_context": structured_context,
        "structured_evidence": structured_evidence,
        "notes": background_notes,
    }

    state["reference_background"] = reference_background[:2000]
    state["preknowledge_notes"] = background_notes
    state["topic_foundation"] = topic_foundation
    state["enriched_context"] = rag_context
    state["preknowledge_evidence"] = structured_evidence
    state["preknowledge_context"] = structured_context
    return state
