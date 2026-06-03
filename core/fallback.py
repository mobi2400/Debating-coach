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
    """Return a callable LLM proxy that tries the routed model first, then
    falls back down FALLBACK_CHAINS on real errors.

    The old implementation pre-flighted each candidate with `invoke("ping")`,
    which doubled API calls (every node burned an extra token round-trip) and
    didn't actually predict 429s on the real call. Now we return a proxy that
    only attempts each model when invoked, so a failure to talk to the
    primary model is the trigger for fallback — not a speculative health
    check.
    """
    primary_key = route_by_task(state)
    chain = FALLBACK_CHAINS.get(primary_key, ["balanced"])
    return _FallbackLLM(chain)


class _FallbackLLM:
    """Tries `chain[0]`, falls through to subsequent keys on exception."""

    def __init__(self, chain: list[str]):
        self.chain = chain

    def invoke(self, prompt):
        last_exc = None
        for key in self.chain:
            llm = LLM_POOL.get(key)
            if llm is None:
                continue
            try:
                return llm.invoke(prompt)
            except Exception as exc:
                logger.warning("LLM '%s' failed: %s. Trying next in chain.", key, exc)
                last_exc = exc

        logger.error("All LLMs in fallback chain failed.")
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("No LLMs available in fallback chain.")
