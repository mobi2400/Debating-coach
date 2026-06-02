import json

from core.fallback import get_llm_with_fallback


def _heuristic_filter(raw_articles: list[dict]) -> list[dict]:
    seen = set()
    filtered = []
    for article in raw_articles:
        title = article.get("title", "").strip().lower()
        url = article.get("url", "").strip().lower()
        dedupe_key = url or title
        if not dedupe_key or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        filtered.append(article)
    return filtered


def filter_node(state: dict) -> dict:
    state["task_type"] = "filter"
    raw_articles = state.get("raw_articles", [])
    default_filtered = _heuristic_filter(raw_articles)

    if not raw_articles:
        state["raw_articles"] = []
        return state

    prompt = (
        "You are filtering research results for a debate digest.\n"
        "Return JSON only: an array of integer indexes to keep.\n"
        "Keep results that are relevant, non-duplicative, and credible.\n\n"
        f"Topic: {state['topic']}\n"
        f"Articles: {json.dumps(raw_articles, ensure_ascii=False)}"
    )

    try:
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        indexes = json.loads(str(content))
        state["raw_articles"] = [
            raw_articles[index]
            for index in indexes
            if isinstance(index, int) and 0 <= index < len(raw_articles)
        ] or default_filtered
    except Exception:
        state["raw_articles"] = default_filtered

    return state
