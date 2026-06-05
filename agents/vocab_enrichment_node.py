from __future__ import annotations

import json
import re

from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node
from tools.tavily_tool import tavily_search


WORD_HINTS = {
    "cogent": "clear, logical, and convincing",
    "nuance": "a subtle but important distinction",
    "lucid": "clear and easy to follow",
    "salient": "most important or most noticeable",
    "incisive": "sharp, direct, and analytically strong",
    "tenuous": "weak, fragile, or not strongly supported",
    "plausible": "seemingly reasonable or likely to be true",
    "coherent": "internally consistent and logically connected",
    "robust": "strong enough to survive pressure or criticism",
    "entrenched": "deeply rooted and hard to dislodge",
    "specious": "appearing persuasive but actually weak",
    "equitable": "fair in a way that accounts for structural differences",
    "contingent": "dependent on specific conditions",
    "normative": "concerned with values and what ought to be",
    "instrumental": "used as a means to achieve another goal",
    "disproportionate": "too large relative to what is justified",
    "asymmetry": "an imbalance of power, information, or burden",
    "precarious": "unstable and vulnerable to collapse",
    "empirical": "grounded in evidence rather than intuition",
    "plenary": "full, complete, and not limited by external checks",
    "coercive": "using pressure or force to shape behaviour",
    "credible": "believable enough to influence how others act",
    "escalatory": "likely to intensify conflict or retaliation",
    "deterrent": "able to discourage an action by raising the cost",
}

STOPWORDS = {
    "article", "analysis", "debate", "topic", "today", "their", "there", "these", "those",
    "which", "would", "because", "between", "power", "state", "global", "international",
}


def _extract_words(text: str, limit: int = 10) -> list[str]:
    seen: list[str] = []
    for token in re.findall(r"\b[a-zA-Z]{6,16}\b", text):
        lowered = token.lower()
        if lowered in STOPWORDS:
            continue
        if lowered not in WORD_HINTS:
            continue
        if lowered not in seen:
            seen.append(lowered)
        if len(seen) >= limit:
            break
    return seen


def _context_lines(lead_case: dict, companion_articles: list[dict], rag_context: str) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    candidate_words: list[str] = []

    title = str(lead_case.get("title", "")).strip()
    content = str(lead_case.get("content", ""))[:1200]
    if title or content:
        lines.append(f"LEAD CASE\nTitle: {title}\nText: {content}")
        candidate_words.extend(_extract_words(f"{title} {content}", limit=6))

    for article in companion_articles[:2]:
        companion_title = str(article.get("title", "")).strip()
        companion_content = str(article.get("content", ""))[:800]
        lines.append(f"COMPANION ANALYSIS\nTitle: {companion_title}\nText: {companion_content}")
        for word in _extract_words(f"{companion_title} {companion_content}", limit=5):
            if word not in candidate_words:
                candidate_words.append(word)

    if rag_context:
        lines.append(f"DEBATE RAG CONTEXT\n{rag_context[:1400]}")
        for word in _extract_words(rag_context, limit=5):
            if word not in candidate_words:
                candidate_words.append(word)

    return lines, candidate_words[:10]


def _heuristic_vocab(topic: str, candidates: list[str]) -> tuple[list[str], list[str]]:
    selected = candidates[:3] or ["cogent", "nuance", "lucid"]
    notes = []
    for word in selected[:3]:
        notes.append(
            f"{word}: {WORD_HINTS.get(word, 'use this for sharper analysis')} | Use it when explaining {topic} more precisely."
        )
    return selected[:3], notes[:3]


def vocab_enrichment_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    lead_case = state.get("lead_case", {}) or {}
    title = str(lead_case.get("title", "")).strip()

    companion_articles = tavily_search(f"{title or topic} debate analysis mechanism implications language")[:3]
    debate_rag = format_retrieved_context(retrieve_for_node("coach_node", f"{topic} {title} debate language framing"))
    context_lines, candidate_words = _context_lines(lead_case, companion_articles, debate_rag)
    fallback_words, fallback_notes = _heuristic_vocab(topic, candidate_words)

    if not context_lines:
        state["vocab_candidates"] = fallback_words
        state["vocab_context_notes"] = fallback_notes
        return state

    prompt = (
        "You are selecting vocabulary for a debate student.\n"
        "Use the lead case, companion analysis, and debate RAG context below.\n"
        "Return JSON only with keys: vocab_candidates, vocab_context_notes.\n"
        "Pick 3 words max.\n"
        "Each word must be genuinely useful in debate, relevant to the case, and not decorative.\n"
        "Each note should explain why the word matters in this specific debate context.\n"
        "Prefer words that appear in serious analytical prose, not generic dictionary words.\n\n"
        f"Topic: {topic}\n"
        f"Candidate words already seen in source text: {candidate_words}\n\n"
        + "\n\n".join(context_lines)
    )

    try:
        state["task_type"] = "structured"
        llm = get_llm_with_fallback(state)
        response = cached_invoke(llm, prompt, scope="vocab_enrichment")
        parsed = json.loads(str(getattr(response, "content", response)))
        vocab_candidates = parsed.get("vocab_candidates") if isinstance(parsed, dict) else None
        vocab_context_notes = parsed.get("vocab_context_notes") if isinstance(parsed, dict) else None

        cleaned_words = []
        for word in vocab_candidates or []:
            clean = str(word).strip().lower()
            if clean and clean not in cleaned_words:
                cleaned_words.append(clean)
            if len(cleaned_words) >= 3:
                break

        cleaned_notes = []
        for note in vocab_context_notes or []:
            clean = " ".join(str(note).split()).strip()
            if clean:
                cleaned_notes.append(clean)
            if len(cleaned_notes) >= 3:
                break

        state["vocab_candidates"] = cleaned_words or fallback_words
        state["vocab_context_notes"] = cleaned_notes or fallback_notes
    except Exception:
        state["vocab_candidates"] = fallback_words
        state["vocab_context_notes"] = fallback_notes

    return state
