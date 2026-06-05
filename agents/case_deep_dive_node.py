from __future__ import annotations

from core.topic_utils import topic_name
from tools.tavily_tool import tavily_search


def _sentences(text: str, limit: int = 3) -> list[str]:
    parts: list[str] = []
    for raw in str(text).replace("\n", " ").split(". "):
        sentence = " ".join(raw.split()).strip(" -")
        if sentence:
            parts.append(sentence.rstrip(".") + ".")
        if len(parts) >= limit:
            break
    return parts


def case_deep_dive_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    lead_case = state.get("lead_case", {}) or {}
    title = str(lead_case.get("title", "")).strip()
    if not title:
        state["case_deep_dive"] = []
        return state

    query = f"{title} {topic} analysis mechanism implications"
    deep_results = tavily_search(query)
    notes: list[str] = []

    for article in deep_results[:2]:
        if str(article.get("title", "")).strip().lower() == title.lower():
            continue
        notes.extend(_sentences(article.get("content", ""), limit=2))
        if len(notes) >= 4:
            break

    if not notes:
        notes = _sentences(lead_case.get("content", ""), limit=3)

    state["case_deep_dive"] = notes[:4]
    return state
