import json
import re

from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node


MAX_RAG_CHARS = 2500


STOPWORDS = {
    "about",
    "after",
    "before",
    "because",
    "between",
    "debate",
    "english",
    "lesson",
    "meaning",
    "power",
    "student",
    "their",
    "there",
    "these",
    "those",
    "today",
    "which",
    "would",
}

BLOCKED_WORDS = {
    "vocabulary",
    "source",
    "norman",
    "easykno",
    "ersary",
    "chapter",
    "session",
    "preview",
    "review",
}

CURATED_WORD_BANK = [
    {
        "word": "cogent",
        "meaning": "clear, logical, and convincing",
        "upgrade_from": "good",
        "example": "Your model is not cogent unless you prove why states comply.",
        "root": "cogn",
    },
    {
        "word": "nuance",
        "meaning": "a subtle but important distinction",
        "upgrade_from": "difference",
        "example": "The nuance is that harm comes from the mechanism, not the headline.",
        "root": "nua",
    },
    {
        "word": "lucid",
        "meaning": "clear and easy to follow",
        "upgrade_from": "clear",
        "example": "Make the opening lucid enough that a judge can track your clash instantly.",
        "root": "luc",
    },
    {
        "word": "salient",
        "meaning": "most important or most noticeable",
        "upgrade_from": "important",
        "example": "The salient comparison is not freedom in theory but power in practice.",
        "root": "sal",
    },
    {
        "word": "incisive",
        "meaning": "sharp, direct, and analytically strong",
        "upgrade_from": "smart",
        "example": "An incisive rebuttal attacks the warrant, not just the wording.",
        "root": "cid",
    },
]


def _extract_candidates(rag_context: str) -> tuple[list[str], list[str]]:
    words = []
    roots = []

    for token in re.findall(r"\b[a-zA-Z]{5,14}\b", rag_context):
        lowered = token.lower()
        if lowered in STOPWORDS or lowered in BLOCKED_WORDS:
            continue
        if not lowered.isalpha():
            continue
        if lowered not in words:
            words.append(lowered)
        if len(words) >= 5:
            break

    for match in re.findall(r"\b([a-zA-Z]{2,6})[-:]", rag_context):
        lowered = match.lower()
        if lowered in BLOCKED_WORDS:
            continue
        if lowered not in roots:
            roots.append(lowered)
        if len(roots) >= 3:
            break

    return words[:5], roots[:3]


def _guess_meaning(word: str) -> str:
    hints = {
        "lucid": "clear and easy to understand",
        "precise": "exact and carefully stated",
        "nuance": "a subtle difference in meaning or tone",
        "cogent": "clear, logical, and convincing",
        "salient": "most noticeable or most important",
        "incisive": "sharp, direct, and analytically powerful",
    }
    return hints.get(word.lower(), "a useful high-precision word for analysis and argument")


def _heuristic_english_lesson(topic: str, rag_context: str) -> tuple[str, list[str], list[str]]:
    vocab_words, word_roots = _extract_candidates(rag_context)
    bank_index = abs(hash(topic)) % len(CURATED_WORD_BANK)
    primary = CURATED_WORD_BANK[bank_index]
    secondary = CURATED_WORD_BANK[(bank_index + 1) % len(CURATED_WORD_BANK)]

    if not vocab_words:
        vocab_words = [primary["word"], secondary["word"]]
    if not word_roots:
        word_roots = [primary["root"], secondary["root"]]

    primary_word = vocab_words[0]
    support_word = vocab_words[1] if len(vocab_words) > 1 else secondary["word"]
    root = word_roots[0]

    lesson_lines = [
        "ENGLISH POWER",
        f"Word: {primary_word}",
        f"Meaning: {_guess_meaning(primary_word)}",
        f"Upgrade: Use '{primary_word}' instead of vague words like '{primary.get('upgrade_from', 'good')}'.",
        f"Debate line: {primary.get('example')}",
        f"Bonus word: {support_word} = {_guess_meaning(support_word)}",
        f"Root: {root} -> learn the root and use one word from it in tomorrow's speech.",
    ]
    return "\n".join(lesson_lines), vocab_words, word_roots


def english_coach_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    rag_chunks = retrieve_for_node("english_coach_node", topic)
    rag_context = format_retrieved_context(rag_chunks)
    default_lesson, default_words, default_roots = _heuristic_english_lesson(
        topic, rag_context
    )

    if not rag_context:
        state["english_lesson"] = default_lesson
        state["vocab_words"] = default_words
        state["word_roots"] = default_roots
        return state

    prompt = (
        "You are teaching English from Word Power Made Easy for a debate student.\n"
        "Return JSON only with keys: english_lesson, vocab_words, word_roots.\n"
        "Teach 3-5 useful words or roots and connect them to speaking, argument precision, or specification knowledge.\n\n"
        f"Topic: {topic}\n"
        f"English RAG context: {rag_context[:MAX_RAG_CHARS]}"
    )

    try:
        state["task_type"] = "structured"
        llm = get_llm_with_fallback(state)
        response = cached_invoke(llm, prompt, scope="english_coach")
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
