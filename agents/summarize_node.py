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


_PER_ARTICLE_TEMPLATE = (
    "You are summarizing one article for a debate student. Topic: {topic}\n\n"
    "Article Title: {title}\n"
    "Article Content: {content}\n\n"
    "Additional Context from Knowledge Base:\n{enriched}\n\n"
    "Write in simple language a non-debate expert can understand.\n\n"
    "Return EXACTLY in this format:\n"
    "SUMMARY:\n- [point 1]\n- [point 2]\n- [point 3]\n\n"
    "KEY FACT: [one specific fact or statistic from this article]\n"
    "CONCEPT: [one key concept or term from this article]"
)


def _parse_per_article_block(text: str) -> tuple[str, str, str]:
    summary_part = text
    if "KEY FACT:" in text:
        summary_part, rest = text.split("KEY FACT:", 1)
        fact = rest.split("\n")[0].strip()
        concept = ""
        if "CONCEPT:" in rest:
            concept = rest.split("CONCEPT:", 1)[1].split("\n")[0].strip()
    else:
        fact, concept = "", ""
    return summary_part.strip(), fact, concept


def summarize_node(state: dict) -> dict:
    state["task_type"] = "summarize"
    ranked_articles = state.get("ranked_articles", [])
    enriched_context = state.get("enriched_context", "")

    if not ranked_articles:
        state["summaries"] = []
        state["key_facts"] = []
        state["concepts"] = []
        return state

    default_summaries, default_facts, default_concepts = _heuristic_summaries(
        state["topic"], ranked_articles, enriched_context
    )

    summaries: list[str] = []
    key_facts: list[str] = []
    concepts: list[str] = []

    try:
        llm = get_llm_with_fallback(state)
    except Exception:
        llm = None

    for index, article in enumerate(ranked_articles):
        if llm is None:
            summaries.append(default_summaries[index])
            key_facts.append(default_facts[index])
            concepts.append(default_concepts[index])
            continue

        prompt = _PER_ARTICLE_TEMPLATE.format(
            topic=state["topic"],
            title=article.get("title", ""),
            content=article.get("content", "")[:8000],
            enriched=enriched_context[:4000] if index == 0 else "",
        )

        try:
            response = llm.invoke(prompt)
            text = str(getattr(response, "content", response)).strip()
            summary_text, fact, concept = _parse_per_article_block(text)
            summaries.append(summary_text or default_summaries[index])
            key_facts.append(fact or default_facts[index])
            concepts.append(concept or default_concepts[index])
        except Exception as exc:
            print(f"[Summarize] Error on article {index}: {exc}")
            summaries.append(default_summaries[index])
            key_facts.append(default_facts[index])
            concepts.append(default_concepts[index])

    state["summaries"] = summaries
    state["key_facts"] = key_facts
    state["concepts"] = concepts
    return state
