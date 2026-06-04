from concurrent.futures import ThreadPoolExecutor, wait

from core.topic_utils import topic_name, topic_search_query
from tools.ddg_tool import ddg_search
from tools.rss_tool import rss_fetch
from tools.tavily_tool import tavily_search
from tools.wiki_tool import wiki_search


RESEARCH_TIMEOUT_SECONDS = 20


def research_node(state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    topic_info = state.get("topic_info", {}) or {}
    search_query = topic_search_query(topic, topic_info)
    raw_articles = []
    reference_background = ""

    jobs = {
        "tavily": lambda: tavily_search(search_query),
        "wiki": lambda: wiki_search(topic),
        "rss": lambda: rss_fetch(topic),
        "ddg": lambda: ddg_search(search_query),
    }

    executor = ThreadPoolExecutor(max_workers=len(jobs))
    future_map = {
        executor.submit(job): name
        for name, job in jobs.items()
    }
    done, pending = wait(future_map, timeout=RESEARCH_TIMEOUT_SECONDS)

    for future in done:
        source_name = future_map[future]
        try:
            result = future.result()
        except Exception as exc:
            print(f"[Research] {source_name} failed: {exc}")
            continue

        if isinstance(result, list):
            raw_articles.extend(result)
        elif isinstance(result, dict) and result:
            if source_name == "wiki":
                reference_background = str(result.get("content", "")).strip()
            else:
                raw_articles.append(result)

    for future in pending:
        source_name = future_map[future]
        future.cancel()
        print(f"[Research] {source_name} timed out after {RESEARCH_TIMEOUT_SECONDS}s")

    executor.shutdown(wait=False, cancel_futures=True)

    state["raw_articles"] = raw_articles
    state["reference_background"] = reference_background[:2000]
    state["task_type"] = "fetch"
    state["article_length"] = max((len(article.get("content", "")) for article in raw_articles), default=0)
    return state
