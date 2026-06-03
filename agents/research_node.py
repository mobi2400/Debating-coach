from core.topic_utils import topic_name
from tools.ddg_tool import ddg_search
from tools.rss_tool import rss_fetch
from tools.tavily_tool import tavily_search
from tools.wiki_tool import wiki_search


def research_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    raw_articles = []

    raw_articles.extend(tavily_search(topic))

    wiki_result = wiki_search(topic)
    if wiki_result:
        raw_articles.append(wiki_result)

    raw_articles.extend(rss_fetch(topic))
    raw_articles.extend(ddg_search(topic))

    state["raw_articles"] = raw_articles
    state["task_type"] = "fetch"
    state["article_length"] = max((len(article.get("content", "")) for article in raw_articles), default=0)
    return state
