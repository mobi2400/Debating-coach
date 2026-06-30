from __future__ import annotations

from core.topic_utils import topic_name
from rag.evidence_organizer import format_structured_evidence, organize_evidence
from rag.retrieval_pipeline import format_retrieved_context, retrieve_bundle_for_node
from tools.wiki_tool import wiki_search


def _context_sentences(text: str, limit: int = 4) -> list[str]:
    parts: list[str] = []
    for raw in str(text).replace("\n", " ").split(". "):
        sentence = " ".join(raw.split()).strip(" -")
        if sentence:
            parts.append(sentence.rstrip(".") + ".")
        if len(parts) >= limit:
            break
    return parts


STAKEHOLDER_HINTS = ("government", "state", "court", "students", "workers", "women", "men", "party", "university", "police", "companies")


def _stakeholders(article_text: str) -> list[str]:
    lowered = article_text.lower()
    found: list[str] = []
    for token in STAKEHOLDER_HINTS:
        if token in lowered and token not in found:
            found.append(token)
        if len(found) >= 4:
            break
    return found


def article_context_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    lead_case = state.get("lead_case", {}) or {}
    lead_title = str(lead_case.get("title", "")).strip()
    lead_content = str(lead_case.get("content", "")).strip()
    query = lead_title or topic

    wiki = wiki_search(query) if query else {}
    article_background = str(wiki.get("content", "")).strip() if isinstance(wiki, dict) else ""
    if not article_background:
        article_background = lead_content

    rag_query = f"{topic} {lead_title} context stakeholders background controversy".strip()
    bundle = retrieve_bundle_for_node("article_context_node", rag_query, state=state)
    rag_chunks = bundle["chunks"]
    rag_context = format_retrieved_context(rag_chunks)
    structured_evidence = organize_evidence(rag_chunks)
    structured_context = format_structured_evidence(structured_evidence, per_section=2)

    state.setdefault("retrieval_plans", {})["article_context_node"] = bundle["plan"] or {}
    state.setdefault("retrieval_traces", {})["article_context_node"] = bundle["trace"]

    context_notes = _context_sentences(article_background, limit=4)
    if not context_notes:
        context_notes = _context_sentences(lead_content, limit=4)

    article_context = {
        "title": lead_title,
        "overview": article_background[:2000],
        "stakeholders": _stakeholders(f"{lead_title} {lead_content} {article_background}"),
        "retrieved_context": rag_context,
        "structured_context": structured_context,
        "structured_evidence": structured_evidence,
        "notes": context_notes,
    }

    topic_context = str((state.get("topic_foundation", {}) or {}).get("retrieved_context", "")).strip()
    combined = "\n\n".join(part for part in (topic_context, rag_context) if part).strip()

    state["article_background"] = article_background[:2000]
    state["article_context_notes"] = context_notes
    state["article_context"] = article_context
    state["enriched_context"] = combined or topic_context or rag_context
    return state
