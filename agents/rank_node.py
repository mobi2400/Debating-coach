import json
from datetime import datetime

from core.fallback import get_llm_with_fallback
from core.topic_utils import topic_name


DEBATE_PRIORITY_TERMS = {
    "debate",
    "policy",
    "rights",
    "justice",
    "freedom",
    "speech",
    "power",
    "state",
    "economy",
    "ethics",
    "law",
    "governance",
    "institution",
    "technology",
    "ai",
}

# Reference / encyclopedia sources — useful for background, terrible as
# "today's case". We still let them rank, just never near the top.
REFERENCE_SOURCES = {"wikipedia", "britannica"}
REFERENCE_DOMAINS = (
    "wikipedia.org",
    "britannica.com",
    "encyclopedia.com",
    "wiktionary.org",
    "wikiquote.org",
    "scholarpedia.org",
)

# Lightweight allow-list of news-flavoured publishers so the heuristic can
# float a real current-affairs piece to position 0 when one is available.
NEWS_SOURCES = {"rss", "tavily", "duckduckgo"}
NEWS_DOMAIN_HINTS = (
    "bbc.",
    "aljazeera.",
    "reuters.",
    "apnews.",
    "thehindu.",
    "ndtv.",
    "hindustantimes.",
    "indianexpress.",
    "theguardian.",
    "nytimes.",
    "ft.com",
    "wsj.com",
    "economist.com",
    "bloomberg.",
    "cnn.",
    "nbcnews.",
    "scroll.in",
    "thewire.in",
    "livemint.",
    "epw.in",
    "aeon.co",
    "foreignpolicy.",
)


def _is_reference_article(article: dict) -> bool:
    source = str(article.get("source", "")).lower()
    if source in REFERENCE_SOURCES:
        return True
    url = str(article.get("url", "")).lower()
    return any(domain in url for domain in REFERENCE_DOMAINS)


def _is_news_article(article: dict) -> bool:
    if _is_reference_article(article):
        return False
    source = str(article.get("source", "")).lower()
    if source in NEWS_SOURCES:
        url = str(article.get("url", "")).lower()
        # Tavily/DuckDuckGo can also surface wiki pages; rely on the domain
        # hint when the source label alone isn't decisive.
        if source == "rss":
            return True
        if any(hint in url for hint in NEWS_DOMAIN_HINTS):
            return True
    return False


def _recency_score(article: dict) -> int:
    published = article.get("published", "")
    if not published:
        return 0

    try:
        published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        age_hours = max((datetime.now(published_dt.tzinfo) - published_dt).total_seconds() / 3600, 0)
        return max(0, 10 - int(age_hours // 6))
    except Exception:
        return 0


def _heuristic_rank(topic: str, articles: list[dict]) -> list[dict]:
    topic_terms = {term for term in topic.lower().split() if term}

    def score(article: dict):
        content = f"{article.get('title', '')} {article.get('content', '')}".lower()
        relevance = sum(1 for term in topic_terms if term in content)
        debate_value = sum(1 for term in DEBATE_PRIORITY_TERMS if term in content)
        base = (relevance * 5) + (debate_value * 2) + _recency_score(article)
        if _is_news_article(article):
            base += 6  # nudge real news above generic search hits
        if _is_reference_article(article):
            base -= 8  # background only — never the lede
        return base

    return sorted(articles, key=score, reverse=True)[:7]


def _promote_news_first(articles: list[dict]) -> list[dict]:
    """Ensure the top slot is a real news/current-affairs article when one
    exists. Encyclopedia/reference pages get bumped down even if the LLM or
    base score put them first. Stable for everything below position 0."""
    if not articles:
        return articles
    first = articles[0]
    if _is_news_article(first) or not _is_reference_article(first):
        return articles
    for idx in range(1, len(articles)):
        if _is_news_article(articles[idx]):
            promoted = articles[idx]
            return [promoted] + articles[:idx] + articles[idx + 1 :]
    return articles


def _compact_articles(articles: list[dict], content_limit: int = 220) -> list[dict]:
    compact = []
    for article in articles:
        compact.append(
            {
                "title": article.get("title", ""),
                "content": str(article.get("content", ""))[:content_limit],
                "source": article.get("source", ""),
                "published": article.get("published", ""),
            }
        )
    return compact


def rank_node(state: dict) -> dict:
    state["task_type"] = "rank"
    topic = topic_name(state.get("topic"))
    articles = state.get("raw_articles", [])
    default_ranked = _heuristic_rank(topic, articles)

    if not articles:
        state["ranked_articles"] = []
        return state

    if len(articles) <= 2:
        state["ranked_articles"] = _promote_news_first(default_ranked)
        return state

    if len(articles) >= 8:
        state["ranked_articles"] = _promote_news_first(default_ranked)
        return state

    compact_articles = _compact_articles(articles)

    prompt = (
        "You are ranking debate research results.\n"
        "Return JSON only: an array of the best article indexes in descending order.\n"
        "Score for topical relevance, recency, debate usefulness, and personal intellectual growth.\n"
        "Prefer articles that help with argument building, framing, institutional analysis, value clashes, policy tradeoffs, or worldview expansion.\n"
        "Use the uploaded PDFs and their subtopics as a relevance map, but not as a hard boundary.\n"
        "Reward articles that deepen the chosen topic, surface strong debate angles, and expand the user's specification knowledge beyond the immediate PDF wording.\n"
        "Deprioritize shallow updates unless they create strong debate angles.\n\n"
        f"Topic: {topic}\n"
        f"Articles: {json.dumps(compact_articles, ensure_ascii=False)}"
    )

    try:
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        indexes = json.loads(str(content))
        ranked = [
            articles[index]
            for index in indexes
            if isinstance(index, int) and 0 <= index < len(articles)
        ]
        state["ranked_articles"] = _promote_news_first(ranked[:7] or default_ranked)
    except Exception:
        state["ranked_articles"] = _promote_news_first(default_ranked)

    return state
