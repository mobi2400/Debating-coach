import os

from dotenv import load_dotenv
from core.network_utils import clear_broken_local_proxies

try:
    from langchain_tavily import TavilySearch as _Tavily  # current package
except ImportError:  # pragma: no cover - bootstrap envs without langchain-tavily
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults as _Tavily
    except ImportError:
        _Tavily = None

load_dotenv()
clear_broken_local_proxies()


def _build_tavily():
    if _Tavily is None:
        return None
    if not os.getenv("TAVILY_API_KEY"):
        return None

    # langchain_tavily.TavilySearch accepts these kwargs; the deprecated
    # TavilySearchResults accepts the same shape, so the call is identical.
    return _Tavily(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=False,
    )


def _normalize_results(results) -> list[dict]:
    # langchain_tavily.TavilySearch returns a dict like
    #   {"query": "...", "results": [{title,url,content,raw_content,...}], ...}
    # The older TavilySearchResults returned just the list.
    if isinstance(results, dict):
        if results.get("error"):
            print(f"[Tavily] Provider error: {results['error']}")
            return []
        items = results.get("results") or []
    else:
        items = results or []

    return [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", "") or item.get("raw_content", ""),
            "source": "tavily",
            "published": item.get("published_date", "") or "",
        }
        for item in items
    ]


def tavily_search(query: str) -> list:
    """Returns normalized search results: title, url, content, source, published."""
    client = _build_tavily()
    if client is None:
        return []

    try:
        return _normalize_results(client.invoke(query))
    except Exception as exc:
        print(f"[Tavily] Error: {exc}")
        return []
