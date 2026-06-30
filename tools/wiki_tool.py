from __future__ import annotations

import re
from urllib.parse import quote

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

REQUEST_HEADERS = {
    "User-Agent": "DebateCoach/1.0 (research helper)",
    "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
}


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


def _clean_query(query: str) -> str:
    text = " ".join(str(query or "").split()).strip()
    if not text:
        return ""
    for separator in ("|", " - ", " ? "):
        if separator in text:
            text = text.split(separator, 1)[0].strip()
    text = re.sub(r"[‘’“”]", "", text)
    text = re.sub(r"[^\w\s:/()-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _query_variants(query: str) -> list[str]:
    clean = _clean_query(query)
    if not clean:
        return []

    variants: list[str] = []

    def add(value: str):
        normalized = _clean_query(value)
        if normalized and normalized not in variants:
            variants.append(normalized)

    add(clean)
    add(clean.replace(":", " "))

    words = clean.split()
    if len(words) > 6:
        add(" ".join(words[:6]))
    if len(words) > 4:
        add(" ".join(words[:4]))

    generic_map = {
        "feminism and gender": "Feminism",
        "international relations": "International relations",
        "geopolitics": "Geopolitics",
        "economics and finance": "Economics",
    }
    lowered = clean.lower()
    if lowered in generic_map:
        add(generic_map[lowered])

    return variants[:5]


def _normalize_result(title: str, slug: str, content: str, url: str | None = None) -> dict:
    return {
        "title": title,
        "url": url or f"https://en.wikipedia.org/wiki/{slug}",
        "content": content,
        "source": "wikipedia",
        "published": "",
    }


def _rest_summary(query: str) -> dict:
    if requests is None:
        return {}

    for candidate in _query_variants(query):
        slug = quote(candidate.replace(" ", "_"), safe="()_")
        try:
            response = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
                headers=REQUEST_HEADERS,
                timeout=10,
            )
            if response.status_code == 404:
                continue
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            if "json" not in content_type:
                continue
            payload = response.json()
            extract = str(payload.get("extract", "")).strip()
            if not extract:
                continue
            return _normalize_result(
                payload.get("title", candidate),
                candidate.replace(" ", "_"),
                extract,
                payload.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{candidate.replace(' ', '_')}"),
            )
        except Exception as rest_exc:
            print(f"[Wikipedia] REST error for '{candidate}': {rest_exc}")
            continue
    return {}


def _langchain_summary(query: str) -> dict:
    if _wiki is None:
        return {}
    for candidate in _query_variants(query):
        try:
            result = _wiki.invoke(candidate)
            content = str(result).strip()
            if not content or content in {"[]", "{}", "None"}:
                continue
            return _normalize_result(candidate, candidate.replace(" ", "_"), content)
        except Exception:
            continue
    return {}


def _library_summary(query: str) -> dict:
    if wikipedia is None:
        return {}
    for candidate in _query_variants(query):
        try:
            summary = wikipedia.summary(candidate, sentences=3, auto_suggest=True)
            page = wikipedia.page(candidate, auto_suggest=True)
            return _normalize_result(page.title, page.title.replace(" ", "_"), summary, page.url)
        except Exception:
            continue
    return {}


def wiki_search(query: str) -> dict:
    """Returns one normalized article-shaped dict for background context."""
    for resolver in (_rest_summary, _langchain_summary, _library_summary):
        result = resolver(query)
        if result:
            return result
    return {}
