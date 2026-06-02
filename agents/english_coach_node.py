import json
import re

from core.fallback import get_llm_with_fallback
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node


def _extract_candidates(rag_context: str) -> tuple[list[str], list[str]]:
    words = []
    roots = []

    for token in re.findall(r"\b[a-zA-Z]{5,}\b", rag_context):
        lowered = token.lower()
        if lowered not in words:
            words.append(lowered)
        if len(words) >= 5:
            break

    for match in re.findall(r"\b([a-zA-Z]{2,6})[-:]", rag_context):
        lowered = match.lower()
        if lowered not in roots:
            roots.append(lowered)
        if len(roots) >= 3:
            break

    return words[:5], roots[:3]


def _heuristic_english_lesson(topic: str, rag_context: str) -> tuple[str, list[str], list[str]]:
    vocab_words, word_roots = _extract_candidates(rag_context)
    if not vocab_words:
        vocab_words = ["lucid", "precise", "nuance"]
    if not word_roots:
        word_roots = ["dict", "cred", "bene"]

    lesson_lines = [
        "ENGLISH POWER",
        f"Word set for stronger debate on {topic}: " + ", ".join(vocab_words[:3]),
        f"Root focus: {', '.join(word_roots[:2])}",
        f"Use '{vocab_words[0]}' when you want your claim to sound sharper and more precise.",
        f"Try linking the root '{word_roots[0]}' to meaning and then use it in one debate sentence today.",
    ]
    return "\n".join(lesson_lines), vocab_words, word_roots


def english_coach_node(state: dict) -> dict:
    rag_chunks = retrieve_for_node("english_coach_node", state["topic"])
    rag_context = format_retrieved_context(rag_chunks)
    default_lesson, default_words, default_roots = _heuristic_english_lesson(
        state["topic"], rag_context
    )

    prompt = (
        "You are teaching English from Word Power Made Easy for a debate student.\n"
        "Return JSON only with keys: english_lesson, vocab_words, word_roots.\n"
        "Teach 3-5 useful words or roots and connect them to speaking, argument precision, or specification knowledge.\n\n"
        f"Topic: {state['topic']}\n"
        f"English RAG context: {rag_context[:5000]}"
    )

    try:
        state["task_type"] = "structured"
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        parsed = json.loads(str(content))
        state["english_lesson"] = parsed.get("english_lesson") or default_lesson
        state["vocab_words"] = parsed.get("vocab_words") or default_words
        state["word_roots"] = parsed.get("word_roots") or default_roots
    except Exception:
        state["english_lesson"] = default_lesson
        state["vocab_words"] = default_words
        state["word_roots"] = default_roots

    return state
