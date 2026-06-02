try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    END = None
    StateGraph = None

from agents.filter_node import filter_node
from agents.rag_enrich_node import rag_enrich_node
from agents.rank_node import rank_node
from agents.research_node import research_node
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
            [research_node, rag_enrich_node, filter_node, rank_node]
        )

    graph = StateGraph(AgentState)
    graph.add_node("research", research_node)
    graph.add_node("rag_enrich", rag_enrich_node)
    graph.add_node("filter", filter_node)
    graph.add_node("rank", rank_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "rag_enrich")
    graph.add_edge("rag_enrich", "filter")
    graph.add_edge("filter", "rank")
    graph.add_edge("rank", END)

    return graph.compile()
