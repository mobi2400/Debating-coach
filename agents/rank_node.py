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
        return (relevance * 5) + (debate_value * 2) + _recency_score(article)

    return sorted(articles, key=score, reverse=True)[:7]


def rank_node(state: dict) -> dict:
    state["task_type"] = "rank"
    topic = topic_name(state.get("topic"))
    articles = state.get("raw_articles", [])
    default_ranked = _heuristic_rank(topic, articles)

    if not articles:
        state["ranked_articles"] = []
        return state

    prompt = (
        "You are ranking debate research results.\n"
        "Return JSON only: an array of the best article indexes in descending order.\n"
        "Score for topical relevance, recency, debate usefulness, and personal intellectual growth.\n"
        "Prefer articles that help with argument building, framing, institutional analysis, value clashes, policy tradeoffs, or worldview expansion.\n"
        "Use the uploaded PDFs and their subtopics as a relevance map, but not as a hard boundary.\n"
        "Reward articles that deepen the chosen topic, surface strong debate angles, and expand the user's specification knowledge beyond the immediate PDF wording.\n"
        "Deprioritize shallow updates unless they create strong debate angles.\n\n"
        f"Topic: {topic}\n"
        f"Articles: {json.dumps(articles, ensure_ascii=False)}"
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
        state["ranked_articles"] = ranked[:7] or default_ranked
    except Exception:
        state["ranked_articles"] = default_ranked

    return state
