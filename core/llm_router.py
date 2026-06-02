from core.llm_pool import LLM_POOL
from core.state import AgentState

ROUTING_MAP = {
    "fetch": "long_ctx",
    "filter": "fast",
    "rank": "fast",
    "summarize": "balanced",
    "argue": "reasoning",
    "debate": "best",
    "format": "structured",
    "quiz": "structured",
    "bedtime": "balanced",
    "weekend": "reasoning",
}


def route_by_task(state: AgentState) -> str:
    task = state.get("task_type", "balanced")
    article_length = state.get("article_length", 0)

    if article_length > 8000:
        return "long_ctx"

    return ROUTING_MAP.get(task, "balanced")


def get_llm(state: AgentState):
    return LLM_POOL[route_by_task(state)]
