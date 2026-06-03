import json

from core.fallback import get_llm_with_fallback
from core.topic_utils import topic_name


DEBATE_GROWTH_SIGNALS = {
    "debate",
    "argument",
    "policy",
    "ethics",
    "rights",
    "justice",
    "freedom",
    "state",
    "power",
    "economy",
    "geopolitics",
    "international",
    "society",
    "law",
    "institution",
    "education",
    "ai",
    "technology",
}


def _heuristic_filter(raw_articles: list[dict]) -> list[dict]:
    seen = set()
    filtered = []
    for article in raw_articles:
        title = article.get("title", "").strip().lower()
        url = article.get("url", "").strip().lower()
        content = article.get("content", "").strip().lower()
        dedupe_key = url or title
        if not dedupe_key or dedupe_key in seen:
            continue

        signal_count = sum(1 for signal in DEBATE_GROWTH_SIGNALS if signal in f"{title} {content}")
        if signal_count == 0 and len(content) < 80:
            continue

        seen.add(dedupe_key)
        filtered.append(article)
    return filtered


def filter_node(state: dict) -> dict:
    state["task_type"] = "filter"
    topic = topic_name(state.get("topic"))
    raw_articles = state.get("raw_articles", [])
    default_filtered = _heuristic_filter(raw_articles)

    if not raw_articles:
        state["raw_articles"] = []
        return state

    prompt = (
        "You are filtering research results for a debate digest.\n"
        "Return JSON only: an array of integer indexes to keep.\n"
        "Keep results that are relevant, non-duplicative, credible, fresh, and valuable for debate preparation.\n"
        "Prefer articles that improve argument quality, framing, comparative analysis, policy understanding, ethical reasoning, or personal intellectual growth.\n"
        "Use the uploaded PDFs and their subtopics as directional guidance for relevance, but do not restrict selection only to articles that mirror those PDF labels exactly.\n"
        "Keep articles that extend, deepen, challenge, or update the PDF themes when they are useful from a debate perspective.\n"
        "Reject generic lifestyle fluff, low-information summaries, entertainment-heavy pieces, and articles with weak debate value.\n\n"
        f"Topic: {topic}\n"
        f"Articles: {json.dumps(raw_articles, ensure_ascii=False)}"
    )

    try:
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        indexes = json.loads(str(content))
        state["raw_articles"] = [
            raw_articles[index]
            for index in indexes
            if isinstance(index, int) and 0 <= index < len(raw_articles)
        ] or default_filtered
    except Exception:
        state["raw_articles"] = default_filtered

    return state
