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

LOW_VALUE_TITLE_PATTERNS = (
    "wikipedia",
    "what is ",
    "introduction",
    "resource guide",
    "program in ",
    "definition",
    "scope, importance",
)

LOW_VALUE_DOMAINS = (
    "wikipedia.org",
    "loc.gov",
    "jgu.edu",
    "library",
)


def _is_low_value_explainer(article: dict) -> bool:
    title = article.get("title", "").strip().lower()
    url = article.get("url", "").strip().lower()
    if any(pattern in title for pattern in LOW_VALUE_TITLE_PATTERNS):
        return True
    return any(domain in url for domain in LOW_VALUE_DOMAINS)


def _is_live_case_candidate(article: dict) -> bool:
    source = article.get("source", "").strip().lower()
    title = article.get("title", "").strip().lower()
    url = article.get("url", "").strip().lower()
    if source == "rss":
        return True
    if source == "tavily" and not _is_low_value_explainer(article):
        return True
    if source == "duckduckgo" and not title.startswith("duckduckgo results for:"):
        return True
    if any(domain in url for domain in ("bbc.", "reuters.", "aljazeera.", "thehindu.", "nytimes.", "foreignpolicy.")):
        return True
    return False


def _heuristic_filter(raw_articles: list[dict]) -> list[dict]:
    seen = set()
    filtered = []
    has_live_candidates = any(_is_live_case_candidate(article) for article in raw_articles)
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
        if has_live_candidates and _is_low_value_explainer(article):
            continue
        if title.startswith("duckduckgo results for:"):
            continue

        seen.add(dedupe_key)
        filtered.append(article)
    return filtered


def _compact_articles(raw_articles: list[dict], content_limit: int = 240) -> list[dict]:
    compact = []
    for article in raw_articles:
        compact.append(
            {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "content": str(article.get("content", ""))[:content_limit],
                "source": article.get("source", ""),
                "published": article.get("published", ""),
            }
        )
    return compact


def filter_node(state: dict) -> dict:
    state["task_type"] = "filter"
    topic = topic_name(state.get("topic"))
    raw_articles = state.get("raw_articles", [])
    default_filtered = _heuristic_filter(raw_articles)

    if not raw_articles:
        state["raw_articles"] = []
        return state

    if len(raw_articles) <= 2:
        state["raw_articles"] = default_filtered
        return state

    if len(raw_articles) >= 8:
        state["raw_articles"] = default_filtered[:6]
        return state

    compact_articles = _compact_articles(raw_articles)

    prompt = (
        "You are filtering research results for a debate digest.\n"
        "Return JSON only: an array of integer indexes to keep.\n"
        "Keep results that are relevant, non-duplicative, credible, fresh, and valuable for debate preparation.\n"
        "Prefer articles that improve argument quality, framing, comparative analysis, policy understanding, ethical reasoning, or personal intellectual growth.\n"
        "Use the uploaded PDFs and their subtopics as directional guidance for relevance, but do not restrict selection only to articles that mirror those PDF labels exactly.\n"
        "Keep articles that extend, deepen, challenge, or update the PDF themes when they are useful from a debate perspective.\n"
        "Reject generic lifestyle fluff, low-information summaries, entertainment-heavy pieces, and articles with weak debate value.\n\n"
        f"Topic: {topic}\n"
        f"Articles: {json.dumps(compact_articles, ensure_ascii=False)}"
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
