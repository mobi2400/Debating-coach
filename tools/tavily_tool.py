import os

from dotenv import load_dotenv

try:
    from langchain_community.tools.tavily_search import TavilySearchResults
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    TavilySearchResults = None

load_dotenv()


def _build_tavily():
    if TavilySearchResults is None:
        return None

    return TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=False,
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
    )


_tavily = _build_tavily()


def tavily_search(query: str) -> list:
    """
    Returns normalized search results.
    Each result follows:
    { title, url, content, source, published }
    """
    if _tavily is None:
        return []

    try:
        results = _tavily.invoke(query)
        return [
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", "") or result.get("raw_content", ""),
                "source": "tavily",
                "published": "",
            }
            for result in results
        ]
    except Exception as exc:
        print(f"[Tavily] Error: {exc}")
        return []
