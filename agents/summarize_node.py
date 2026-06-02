import json
import re

from core.fallback import get_llm_with_fallback


def _sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def _infer_concept(topic: str, article: dict) -> str:
    title = article.get("title", "").strip()
    if title:
        return title[:120]
    return f"Key concept in {topic}"


def _heuristic_summaries(topic: str, ranked_articles: list[dict], enriched_context: str) -> tuple[list[str], list[str], list[str]]:
    summaries = []
    key_facts = []
    concepts = []

    for article in ranked_articles:
        text = article.get("content", "") or article.get("title", "")
        sentences = _sentence_split(text)
        bullets = sentences[:3] if sentences else [f"Relevant debate coverage related to {topic}."]
        if enriched_context and len(bullets) < 4:
            bullets.append("Background context from the knowledge base is available for deeper prep.")

        summary = "\n".join(f"- {bullet}" for bullet in bullets[:4])
        summaries.append(summary)
        key_facts.append(bullets[0][:220])
        concepts.append(_infer_concept(topic, article))

    return summaries, key_facts, concepts


def summarize_node(state: dict) -> dict:
    state["task_type"] = "summarize"
    ranked_articles = state.get("ranked_articles", [])
    enriched_context = state.get("enriched_context", "")

    if not ranked_articles:
        state["summaries"] = []
        state["key_facts"] = []
        state["concepts"] = []
        return state

    prompt = (
        "You are summarizing research for a debate student.\n"
        "Return JSON only with keys: summaries, key_facts, concepts.\n"
        "summaries must be an array of 3-4 bullet layman summaries per article.\n"
        "key_facts must be memorable one-line facts.\n"
        "concepts must be high-value debate concepts extracted from the articles.\n\n"
        f"Topic: {state['topic']}\n"
        f"Enriched context: {enriched_context[:4000]}\n"
        f"Articles: {json.dumps(ranked_articles, ensure_ascii=False)}"
    )

    default_summaries, default_facts, default_concepts = _heuristic_summaries(
        state["topic"], ranked_articles, enriched_context
    )

    try:
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        parsed = json.loads(str(content))

        state["summaries"] = parsed.get("summaries") or default_summaries
        state["key_facts"] = parsed.get("key_facts") or default_facts
        state["concepts"] = parsed.get("concepts") or default_concepts
    except Exception:
        state["summaries"] = default_summaries
        state["key_facts"] = default_facts
        state["concepts"] = default_concepts

    return state
