from core.network_utils import clear_broken_local_proxies

try:
    import requests
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    requests = None

try:
    from langchain_community.tools import WikipediaQueryRun
    from langchain_community.utilities import WikipediaAPIWrapper
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    WikipediaQueryRun = None
    WikipediaAPIWrapper = None

try:
    import wikipedia
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    wikipedia = None


clear_broken_local_proxies()


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
        if not str(result).strip():
            raise ValueError("empty wikipedia response")
        return {
            "title": query,
            "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
            "content": result,
            "source": "wikipedia",
            "published": "",
        }
    except Exception as exc:
        print(f"[Wikipedia] Error: {exc}")
        if wikipedia is None:
            if requests is None:
                return {}
            try:
                slug = query.replace(" ", "_")
                response = requests.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
                    timeout=10,
                )
                response.raise_for_status()
                payload = response.json()
                extract = payload.get("extract", "")
                if not extract:
                    return {}
                return {
                    "title": payload.get("title", query),
                    "url": payload.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{slug}"),
                    "content": extract,
                    "source": "wikipedia",
                    "published": "",
                }
            except Exception as rest_exc:
                print(f"[Wikipedia] REST fallback error: {rest_exc}")
                return {}
        try:
            summary = wikipedia.summary(query, sentences=3, auto_suggest=False)
            page = wikipedia.page(query, auto_suggest=False)
            return {
                "title": page.title,
                "url": page.url,
                "content": summary,
                "source": "wikipedia",
                "published": "",
            }
        except Exception as fallback_exc:
            print(f"[Wikipedia] Fallback error: {fallback_exc}")
            return {}
