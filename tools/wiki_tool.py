try:
    from langchain_community.tools import WikipediaQueryRun
    from langchain_community.utilities import WikipediaAPIWrapper
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    WikipediaQueryRun = None
    WikipediaAPIWrapper = None


def _build_wiki():
    if WikipediaQueryRun is None or WikipediaAPIWrapper is None:
        return None

    return WikipediaQueryRun(
        api_wrapper=WikipediaAPIWrapper(
            top_k_results=2,
            doc_content_chars_max=3000,
            lang="en",
        )
    )


_wiki = _build_wiki()


def wiki_search(query: str) -> dict:
    """
    Returns one normalized article-shaped dict for background context.
    """
    if _wiki is None:
        return {}

    try:
        result = _wiki.invoke(query)
        return {
            "title": query,
            "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
            "content": result,
            "source": "wikipedia",
            "published": "",
        }
    except Exception as exc:
        print(f"[Wikipedia] Error: {exc}")
        return {}
