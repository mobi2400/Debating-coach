try:
    from langchain_community.tools import DuckDuckGoSearchRun
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    DuckDuckGoSearchRun = None


def _build_ddg():
    if DuckDuckGoSearchRun is None:
        return None
    return DuckDuckGoSearchRun()


_ddg = _build_ddg()


def ddg_search(query: str) -> list:
    """
    Returns a normalized list containing DuckDuckGo result text.
    """
    if _ddg is None:
        return []

    try:
        result = _ddg.invoke(query)
        return [
            {
                "title": f"DuckDuckGo results for: {query}",
                "url": "",
                "content": result,
                "source": "duckduckgo",
                "published": "",
            }
        ]
    except Exception as exc:
        print(f"[DuckDuckGo] Error: {exc}")
        return []
