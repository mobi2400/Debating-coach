from __future__ import annotations


ROUTE_MAP = {
    "rag_enrich_node": {
        "intent": "background",
        "stores": ["knowledge_db", "reasoning_db"],
    },
    "argue_node": {
        "intent": "argument_generation",
        "stores": ["reasoning_db", "knowledge_db", "style_db"],
    },
    "coach_node": {
        "intent": "coaching",
        "stores": ["reasoning_db", "style_db", "knowledge_db"],
    },
    "english_coach_node": {
        "intent": "vocabulary",
        "stores": ["english_db"],
    },
}


def route_query(node_name: str, task_type: str | None = None) -> dict:
    route = dict(ROUTE_MAP.get(node_name, {"intent": task_type or "reference", "stores": ["knowledge_db"]}))
    route["task_type"] = task_type or ""
    return route
