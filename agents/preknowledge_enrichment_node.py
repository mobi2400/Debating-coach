from __future__ import annotations

from agents.article_context_node import article_context_node
from agents.topic_foundation_node import topic_foundation_node


def preknowledge_enrichment_node(state: dict) -> dict:
    state = topic_foundation_node(state)
    state = article_context_node(state)
    return state
