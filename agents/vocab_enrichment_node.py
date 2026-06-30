from __future__ import annotations

import json
import re

from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from memory.weekly_store import load_log
from rag.retrieval_pipeline import format_retrieved_context, retrieve_bundle_for_node


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
    for token in re.findall(r"[a-zA-Z]{6,16}", text):
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


def _recent_vocab(limit_days: int = 10) -> set[str]:
    log = load_log()
    recent: set[str] = set()
    days_seen = 0
    for day in sorted(log.keys(), reverse=True):
        entries = log.get(day, [])
        for entry in entries:
            for word in entry.get("vocab_words", []) or []:
                clean = str(word).strip().lower()
                if clean:
                    recent.add(clean)
        days_seen += 1
        if days_seen >= limit_days:
            break
    return recent


def _lesson_texts(state: dict) -> list[str]:
    lesson_texts: list[str] = []

    lead_case = state.get("lead_case", {}) or {}
    lesson_texts.append(str(lead_case.get("title", "")))
    lesson_texts.append(str(lead_case.get("content", ""))[:1200])

    for mapping in (
        state.get("topic_foundation", {}) or {},
        state.get("article_context", {}) or {},
        state.get("drafted_motion", {}) or {},
        state.get("debate_teaching", {}) or {},
    ):
        if not isinstance(mapping, dict):
            continue
        for value in mapping.values():
            if isinstance(value, list):
                lesson_texts.extend(str(item) for item in value[:6] if str(item).strip())
            elif isinstance(value, dict):
                for nested in value.values():
                    if isinstance(nested, list):
                        lesson_texts.extend(str(item) for item in nested[:6] if str(item).strip())
                    elif nested:
                        lesson_texts.append(str(nested))
            elif value:
                lesson_texts.append(str(value))

    for key in (
        "preknowledge_notes",
        "article_context_notes",
        "case_deep_dive",
        "summaries",
        "key_facts",
        "concepts",
        "vocab_context_notes",
    ):
        values = state.get(key, []) or []
        if isinstance(values, list):
            lesson_texts.extend(str(item) for item in values[:6] if str(item).strip())

    arguments = state.get("arguments", {}) or {}
    for side in ("for", "against"):
        lesson_texts.extend(str(item) for item in (arguments.get(side, []) or [])[:3] if str(item).strip())
    middle = arguments.get("middle")
    if middle:
        lesson_texts.append(str(middle))

    return lesson_texts


def _context_lines(state: dict, rag_context: str) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    candidate_words: list[str] = []

    lesson_blob = "\n\n".join(text for text in _lesson_texts(state) if text)
    if lesson_blob:
        lines.append(f"LESSON MATERIAL\n{lesson_blob[:2800]}")
        candidate_words.extend(_extract_words(lesson_blob, limit=8))

    if rag_context:
        lines.append(f"DEBATE RAG CONTEXT\n{rag_context[:1400]}")
        for word in _extract_words(rag_context, limit=5):
            if word not in candidate_words:
                candidate_words.append(word)

    return lines, candidate_words[:10]


def _definition(word: str) -> str:
    return WORD_HINTS.get(word.lower(), "a useful debate word")


def _topic_stub(topic: str) -> str:
    mapping = {
        "feminism and gender": "gender reform",
        "international relations": "international cooperation",
        "geopolitics": "great-power competition",
        "economics and finance": "economic policymaking",
    }
    return mapping.get(topic.lower(), topic)


def _example_line(word: str, topic: str, drafted_motion: dict | None = None) -> str:
    subject = str((drafted_motion or {}).get("case_label", "")).strip() or _topic_stub(topic)
    templates = {
        "coercive": f"A coercive approach to {subject} may force compliance quickly, but it can also trigger backlash if institutions do not trust the reform.",
        "coherent": f"Your opposition case is only coherent if you explain how {subject} can improve without the policy you are rejecting.",
        "credible": f"The reform is only credible if it changes incentives around {subject} instead of producing a symbolic announcement.",
        "robust": f"A robust argument on {subject} survives the obvious pushback about cost, enforcement, and unintended consequences.",
        "plausible": f"Your mechanism must be plausible: explain why real actors in {subject} would behave the way your model predicts.",
        "normative": f"This is a normative claim about {subject}: you are arguing what institutions ought to do, not only what they currently do.",
        "asymmetry": f"The key asymmetry in {subject} is that one side bears the risk first while the other controls the decision.",
        "empirical": f"Make the argument empirical by pointing to a concrete detail from today's {subject} case rather than staying abstract.",
        "contingent": f"The benefit is contingent on enforcement, which means your side must explain what happens if support weakens halfway through.",
        "deterrent": f"A deterrent effect matters only if actors in {subject} actually believe the cost of non-compliance has risen.",
    }
    return templates.get(
        word.lower(),
        f"Use '{word}' when you explain {subject} with a sharper mechanism, clearer comparison, and more precise judge language."
    )


def _heuristic_vocab(topic: str, candidates: list[str], drafted_motion: dict | None = None) -> tuple[list[str], list[str], dict]:
    recent = _recent_vocab()
    fallback_pool = [
        "coercive",
        "credible",
        "deterrent",
        "robust",
        "coherent",
        "plausible",
        "normative",
        "asymmetry",
        "empirical",
        "contingent",
    ]
    selected: list[str] = []
    for source in (candidates, fallback_pool):
        for word in source:
            clean = str(word).strip().lower()
            if not clean or clean in selected or clean in recent:
                continue
            selected.append(clean)
            if len(selected) >= 2:
                break
        if len(selected) >= 2:
            break
    if not selected:
        selected = ["credible", "coherent"]

    notes = []
    structured = []
    for word in selected[:2]:
        meaning = _definition(word)
        example = _example_line(word, topic, drafted_motion)
        notes.append(f"{word}: {meaning} | Example: {example}")
        structured.append(
            {
                "word": word,
                "meaning": meaning,
                "why_it_helps": f"Use it when you want to make your {topic} analysis sharper and more precise.",
                "example": example,
            }
        )
    return selected[:2], notes[:2], {"selected_words": structured}


def vocab_enrichment_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    lead_case = state.get("lead_case", {}) or {}
    title = str(lead_case.get("title", "")).strip()
    recent = _recent_vocab()
    drafted_motion = state.get("drafted_motion", {}) or {}

    bundle = retrieve_bundle_for_node("coach_node", f"{topic} {title} debate language framing", state=state)
    debate_rag = format_retrieved_context(bundle["chunks"])
    state.setdefault("retrieval_plans", {})["vocab_enrichment_node"] = bundle["plan"] or {}
    state.setdefault("retrieval_traces", {})["vocab_enrichment_node"] = bundle["trace"]

    context_lines, candidate_words = _context_lines(state, debate_rag)
    candidate_words = [word for word in candidate_words if word not in recent]
    fallback_words, fallback_notes, fallback_output = _heuristic_vocab(topic, candidate_words, drafted_motion)

    if not context_lines:
        state["vocab_candidates"] = fallback_words
        state["vocab_context_notes"] = fallback_notes
        state["vocabulary_output"] = fallback_output
        return state

    prompt = (
        "You are selecting vocabulary for a debate student.\n"
        "Use the lesson material and debate RAG context below.\n"
        "Return JSON only with keys: vocab_candidates, vocab_context_notes.\n"
        "Pick exactly 2 words if possible, never more than 2.\n"
        "Each word must be genuinely useful in debate, relevant to the lesson, and not decorative.\n"
        "Each note should include a precise meaning and one example of how to use the word in this debate context.\n"
        "Prefer words that already appear in the drafted lesson material before generic fallback vocabulary.\n\n"
        f"Topic: {topic}\n"
        f"Candidate words already seen in lesson material: {candidate_words}\n\n"
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
            if len(cleaned_words) >= 2:
                break

        selected_words = [word for word in cleaned_words if word not in recent] or fallback_words
        parsed_notes = vocab_context_notes if isinstance(vocab_context_notes, list) else []
        notes: list[str] = []
        structured_words = []
        for index, word in enumerate(selected_words[:2]):
            meaning = _definition(word)
            example = _example_line(word, topic, drafted_motion)
            note = parsed_notes[index] if index < len(parsed_notes) and str(parsed_notes[index]).strip() else f"{word}: {meaning} | Example: {example}"
            notes.append(" ".join(str(note).split()).strip())
            structured_words.append(
                {
                    "word": word,
                    "meaning": meaning,
                    "why_it_helps": f"Use it when you want to make your {topic} analysis sharper and more precise.",
                    "example": example,
                }
            )

        state["vocab_candidates"] = selected_words[:2]
        state["vocab_context_notes"] = notes[:2] or fallback_notes
        state["vocabulary_output"] = {"selected_words": structured_words} if structured_words else fallback_output
    except Exception:
        state["vocab_candidates"] = fallback_words
        state["vocab_context_notes"] = fallback_notes
        state["vocabulary_output"] = fallback_output

    return state
