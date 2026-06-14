from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.query_router import route_query


def test_route_query_returns_explicit_node_route():
    route = route_query("coach_node", "debate")

    assert route["intent"] == "coaching"
    assert route["stores"] == ["reasoning_db", "style_db", "knowledge_db"]


def test_route_query_falls_back_for_unknown_node():
    route = route_query("unknown_node", "fetch")

    assert route["intent"] == "fetch"
    assert route["stores"] == ["knowledge_db"]
