try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    END = None
    StateGraph = None

from agents.argue_node import argue_node
from agents.coach_node import coach_node
from agents.english_coach_node import english_coach_node
from agents.filter_node import filter_node
from agents.format_node import format_node
from agents.case_deep_dive_node import case_deep_dive_node
from agents.lead_case_selector import lead_case_selector_node
from agents.night_agent import night_agent_node
from agents.preknowledge_enrichment_node import preknowledge_enrichment_node
from agents.rank_node import rank_node
from agents.research_node import research_node
from agents.summarize_node import summarize_node
from agents.vocab_enrichment_node import vocab_enrichment_node
from agents.weekend_agent import weekend_agent_node
from core.state import AgentState


class LocalSequentialGraph:
    def __init__(self, steps):
        self.steps = steps

    def invoke(self, state: dict):
        for step in self.steps:
            state = step(state)
        return state


def build_daily_graph():
    if StateGraph is None:
        return LocalSequentialGraph(
            [
                research_node,
                filter_node,
                rank_node,
                lead_case_selector_node,
                preknowledge_enrichment_node,
                case_deep_dive_node,
                vocab_enrichment_node,
                summarize_node,
                argue_node,
                coach_node,
                english_coach_node,
                format_node,
            ]
        )

    graph = StateGraph(AgentState)
    graph.add_node("research", research_node)
    graph.add_node("filter", filter_node)
    graph.add_node("rank", rank_node)
    graph.add_node("lead_case_selector", lead_case_selector_node)
    graph.add_node("preknowledge_enrichment", preknowledge_enrichment_node)
    graph.add_node("case_deep_dive", case_deep_dive_node)
    graph.add_node("vocab_enrichment", vocab_enrichment_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("argue", argue_node)
    graph.add_node("coach", coach_node)
    graph.add_node("english_coach", english_coach_node)
    graph.add_node("format", format_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "filter")
    graph.add_edge("filter", "rank")
    graph.add_edge("rank", "lead_case_selector")
    graph.add_edge("lead_case_selector", "preknowledge_enrichment")
    graph.add_edge("preknowledge_enrichment", "case_deep_dive")
    graph.add_edge("case_deep_dive", "vocab_enrichment")
    graph.add_edge("vocab_enrichment", "summarize")
    graph.add_edge("summarize", "argue")
    graph.add_edge("argue", "coach")
    graph.add_edge("coach", "english_coach")
    graph.add_edge("english_coach", "format")
    graph.add_edge("format", END)

    return graph.compile()


def build_night_graph():
    if StateGraph is None:
        return LocalSequentialGraph([night_agent_node])

    graph = StateGraph(AgentState)
    graph.add_node("night", night_agent_node)
    graph.set_entry_point("night")
    graph.add_edge("night", END)
    return graph.compile()


def build_weekend_graph():
    if StateGraph is None:
        return LocalSequentialGraph([weekend_agent_node])

    graph = StateGraph(AgentState)
    graph.add_node("weekend", weekend_agent_node)
    graph.set_entry_point("weekend")
    graph.add_edge("weekend", END)
    return graph.compile()
