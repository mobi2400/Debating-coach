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


def topic_search_query(topic: object, topic_info: dict | None = None) -> str:
    name = topic_name(topic)
    keywords = topic_keywords(topic)

    query_terms: list[str] = [name]
    for keyword in keywords[:4]:
        if keyword not in query_terms:
            query_terms.append(keyword)

    if isinstance(topic_info, dict):
        live_cases = topic_info.get("live_case_studies_with_analytical_value", [])
        if isinstance(live_cases, list):
            for case in live_cases[:1]:
                snippet = str(case).split("—", 1)[0].strip()
                if snippet and snippet.lower() not in " ".join(query_terms).lower():
                    query_terms.append(snippet)

    query_terms.append("latest analysis")
    return " ".join(term for term in query_terms if term).strip()
