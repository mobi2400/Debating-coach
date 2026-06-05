from __future__ import annotations

from agents.rank_node import _is_explainer_article, _is_news_article, _is_reference_article
from core.topic_utils import topic_name


def _article_signal_score(topic: str, article: dict, topic_info: dict) -> tuple[int, int, int, int]:
    title = str(article.get("title", "")).strip()
    content = str(article.get("content", "")).strip().lower()
    title_lower = title.lower()
    live_cases = topic_info.get("live_case_studies_with_analytical_value", []) if isinstance(topic_info, dict) else []
    live_case_hits = 0
    if isinstance(live_cases, list):
        for case in live_cases[:3]:
            snippet = str(case).split("—", 1)[0].split("-", 1)[0].strip().lower()
            if snippet and (snippet in title_lower or snippet in content):
                live_case_hits += 1

    mechanism_terms = ("because", "therefore", "backlash", "sanctions", "veto", "deterr", "sovereign", "institution", "precedent")
    mechanism_hits = sum(1 for term in mechanism_terms if term in content or term in title_lower)
    news_bonus = 2 if _is_news_article(article) else 0
    explainer_penalty = -3 if _is_explainer_article(article) else 0
    reference_penalty = -5 if _is_reference_article(article) else 0
    topic_terms = {term for term in topic.lower().replace(",", " ").split() if term}
    relevance = sum(1 for term in topic_terms if term in f"{title_lower} {content}")
    return (
        live_case_hits + news_bonus + explainer_penalty + reference_penalty,
        mechanism_hits,
        relevance,
        len(title),
    )


def lead_case_selector_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    topic_info = state.get("topic_info", {}) or {}
    candidates = state.get("ranked_articles") or state.get("candidate_articles") or state.get("raw_articles") or []

    if not candidates:
        state["lead_case"] = {}
        state["lead_case_reason"] = "No candidate case was available."
        return state

    lead = max(candidates, key=lambda article: _article_signal_score(topic, article, topic_info))
    lead_score = _article_signal_score(topic, lead, topic_info)

    if _is_news_article(lead):
        reason = "Chosen as the strongest current case with live debate value."
    elif _is_explainer_article(lead):
        reason = "No sharp live case landed, so the clearest teachable explainer was selected."
    else:
        reason = "Chosen as the most debate-rich case after comparing relevance, mechanism, and teachability."

    state["lead_case"] = lead
    state["lead_case_reason"] = f"{reason} score={lead_score}"
    return state
