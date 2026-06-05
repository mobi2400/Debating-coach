import json
import re

from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from memory.weekly_store import load_log
from rag.retrieval_pipeline import format_retrieved_context, retrieve_for_node
from tools.tavily_tool import tavily_search


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
}


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
    return WORD_HINTS.get(word.lower(), "a useful high-precision word for analysis and argument")


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


def _candidate_words_from_articles(state: dict) -> list[str]:
    recent = _recent_vocab()
    article_texts = []
    for article in state.get("ranked_articles", [])[:3]:
        article_texts.append(str(article.get("title", "")))
        article_texts.append(str(article.get("content", ""))[:900])

    topic = topic_name(state.get("topic"))
    if topic:
        for article in tavily_search(f"{topic} debate analysis vocabulary essay")[:2]:
            article_texts.append(str(article.get("title", "")))
            article_texts.append(str(article.get("content", ""))[:700])

    candidates: list[str] = []
    pool = " ".join(article_texts)
    for token in re.findall(r"\b[a-zA-Z]{6,16}\b", pool):
        lowered = token.lower()
        if lowered in STOPWORDS or lowered in BLOCKED_WORDS or lowered in recent:
            continue
        if lowered not in WORD_HINTS:
            continue
        if lowered not in candidates:
            candidates.append(lowered)
    return candidates[:5]


def _rotating_curated_words(topic: str) -> tuple[dict, dict]:
    recent = _recent_vocab()
    ordered = CURATED_WORD_BANK[:]
    ordered.sort(key=lambda item: (item["word"] in recent, abs(hash(f"{topic}:{item['word']}"))))
    primary = ordered[0]
    secondary = next((item for item in ordered[1:] if item["word"] != primary["word"]), ordered[1])
    return primary, secondary


def _heuristic_english_lesson(topic: str, rag_context: str) -> tuple[str, list[str], list[str]]:
    primary, secondary = _rotating_curated_words(topic)
    vocab_words = [primary["word"], secondary["word"]]
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


def _article_driven_lesson(topic: str, candidate_words: list[str]) -> tuple[str, list[str], list[str]]:
    if not candidate_words:
        return _heuristic_english_lesson(topic, "")

    primary_word = candidate_words[0]
    support_word = candidate_words[1] if len(candidate_words) > 1 else "cogent"
    root = primary_word[:4]
    lesson_lines = [
        "ENGLISH POWER",
        f"Word: {primary_word}",
        f"Meaning: {_guess_meaning(primary_word)}",
        f"Upgrade: Use '{primary_word}' when you want your explanation to sound more analytical and debate-ready.",
        f"Debate line: In {topic}, your claim is not {support_word} unless you prove the mechanism and comparative impact.",
        f"Bonus word: {support_word} = {_guess_meaning(support_word)}",
        f"Root: {root} -> notice the root family and reuse one related word tomorrow.",
    ]
    return "\n".join(lesson_lines), [primary_word, support_word], [root]


def english_coach_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    rag_chunks = retrieve_for_node("english_coach_node", topic)
    rag_context = format_retrieved_context(rag_chunks)
    article_candidates = _candidate_words_from_articles(state)
    default_lesson, default_words, default_roots = _heuristic_english_lesson(topic, rag_context)
    if article_candidates:
        default_lesson, default_words, default_roots = _article_driven_lesson(topic, article_candidates)

    if not rag_context and not article_candidates:
        state["english_lesson"] = default_lesson
        state["vocab_words"] = default_words
        state["word_roots"] = default_roots
        return state

    article_context = []
    for article in state.get("ranked_articles", [])[:2]:
        article_context.append(
            f"TITLE: {article.get('title', '')}\nCONTENT: {str(article.get('content', ''))[:700]}"
        )

    prompt = (
        "You are teaching English for a debate student.\n"
        "Return JSON only with keys: english_lesson, vocab_words, word_roots.\n"
        "Teach 3-5 useful words or roots and connect them to speaking, argument precision, or specification knowledge.\n"
        "Do not repeat stale words from recent lessons if fresh article-derived words are available.\n"
        "Prefer high-utility debate words that appear in strong prose from today's article context.\n"
        "The english_lesson should include lines starting with Word:, Meaning:, Upgrade:, Debate line:, Bonus word:, Root:.\n\n"
        f"Topic: {topic}\n"
        f"Recent words to avoid: {sorted(_recent_vocab())[:20]}\n"
        f"Candidate fresh words from article/research: {article_candidates}\n"
        f"Today's article context:\n" + "\n\n".join(article_context) + "\n\n"
        f"English RAG context: {rag_context[:MAX_RAG_CHARS]}"
    )

    try:
        state["task_type"] = "structured"
        llm = get_llm_with_fallback(state)
        response = cached_invoke(llm, prompt, scope="english_coach")
        content = getattr(response, "content", response)
        parsed = json.loads(str(content))
        state["english_lesson"] = parsed.get("english_lesson") or default_lesson
        vocab_words = parsed.get("vocab_words") or default_words
        if article_candidates:
            deduped = []
            for word in list(vocab_words) + article_candidates:
                clean = str(word).strip().lower()
                if clean and clean not in deduped:
                    deduped.append(clean)
                if len(deduped) >= 3:
                    break
            vocab_words = deduped
        state["vocab_words"] = vocab_words
        state["word_roots"] = parsed.get("word_roots") or default_roots
    except Exception:
        state["english_lesson"] = default_lesson
        if article_candidates:
            state["vocab_words"] = (article_candidates + default_words)[:3]
        else:
            state["vocab_words"] = default_words
        state["word_roots"] = default_roots

    return state
