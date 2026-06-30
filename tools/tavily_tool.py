import os
import warnings

from dotenv import load_dotenv
from core.network_utils import clear_broken_local_proxies

try:
    from tavily import TavilyClient
except ImportError:  # pragma: no cover - bootstrap envs without tavily-python
    TavilyClient = None

try:
    from langchain_tavily import TavilySearch as _LangchainTavily
except ImportError:  # pragma: no cover - bootstrap envs without langchain-tavily
    _LangchainTavily = None

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)
        from langchain_community.tools.tavily_search import TavilySearchResults as _DeprecatedTavily
except ImportError:  # pragma: no cover
    _DeprecatedTavily = None

load_dotenv()
clear_broken_local_proxies()


def _build_tavily_direct():
    if TavilyClient is None:
        return None
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None
    return TavilyClient(api_key=api_key)


def _build_tavily_langchain():
    client_cls = _LangchainTavily or _DeprecatedTavily
    if client_cls is None or not os.getenv("TAVILY_API_KEY"):
        return None
    return client_cls(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=False,
    )


def _normalize_results(results) -> list[dict]:
    if isinstance(results, dict):
        if results.get("error"):
            print(f"[Tavily] Provider error: {results['error']}")
            return []
        items = results.get("results") or []
    else:
        items = results or []

    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "") or item.get("raw_content", ""),
                "source": "tavily",
                "published": item.get("published_date", "") or "",
            }
        )
    return normalized


def tavily_search(query: str) -> list:
    """Returns normalized search results: title, url, content, source, published."""
    direct = _build_tavily_direct()
    if direct is not None:
        try:
            response = direct.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                include_answer=True,
                include_raw_content=True,
                include_images=False,
            )
            return _normalize_results(response)
        except Exception as exc:
            print(f"[Tavily] Direct client error: {exc}")

    client = _build_tavily_langchain()
    if client is None:
        return []

    try:
        return _normalize_results(client.invoke(query))
    except Exception as exc:
        print(f"[Tavily] Error: {exc}")
        return []
