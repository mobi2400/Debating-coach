from __future__ import annotations


TOPIC_KEYWORDS = {
    "international relations": ["diplomacy", "sovereignty", "nato", "un", "security", "treaty"],
    "geopolitics": ["geopolitics", "china", "russia", "sanctions", "taiwan", "border", "power"],
    "economics and finance": ["inflation", "interest rates", "trade", "debt", "economy", "market"],
    "feminism and gender": ["gender", "patriarchy", "women", "feminism", "reproductive", "equality"],
    "technology and ai": ["ai", "artificial intelligence", "surveillance", "chips", "platform", "algorithm"],
    "free speech": ["speech", "censorship", "expression", "platform moderation", "press freedom"],
    "state power": ["state", "surveillance", "policing", "executive", "security state", "authority"],
    "education": ["education", "school", "university", "curriculum", "exam", "students"],
    "religion and society": ["religion", "faith", "secular", "blasphemy", "church", "temple"],
    "relationships, intimacy, and social structures": ["family", "marriage", "loneliness", "dating", "intimacy", "social capital"],
}


def topic_name(topic: object) -> str:
    if isinstance(topic, str):
        return topic.strip()

    if isinstance(topic, dict):
        value = topic.get("topic")
        if isinstance(value, str):
            return value.strip()

    if topic is None:
        return ""

    return str(topic).strip()


def topic_keywords(topic: object) -> list[str]:
    name = topic_name(topic).lower()
    keywords = TOPIC_KEYWORDS.get(name, [])
    base_terms = [term for term in name.replace(",", " ").split() if term]
    merged = []
    for term in base_terms + keywords:
        normalized = term.strip().lower()
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged
