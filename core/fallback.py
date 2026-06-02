import logging

from core.llm_pool import LLM_POOL
from core.llm_router import route_by_task
from core.state import AgentState

logger = logging.getLogger(__name__)

FALLBACK_CHAINS = {
    "best": ["best", "reasoning", "balanced"],
    "reasoning": ["reasoning", "balanced", "fast"],
    "balanced": ["balanced", "fast"],
    "structured": ["structured", "balanced", "fast"],
    "long_ctx": ["long_ctx", "balanced"],
    "fast": ["fast", "balanced"],
}


def get_llm_with_fallback(state: AgentState):
    primary_key = route_by_task(state)
    chain = FALLBACK_CHAINS.get(primary_key, ["balanced"])

    for key in chain:
        try:
            llm = LLM_POOL[key]
            llm.invoke("ping")
            return llm
        except Exception as exc:
            logger.warning("LLM '%s' failed: %s. Trying next in chain.", key, exc)

    logger.error("All LLMs in fallback chain failed. Using balanced as last resort.")
    return LLM_POOL["balanced"]
