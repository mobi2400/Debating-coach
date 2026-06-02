from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.ddg_tool import ddg_search
from tools.rss_tool import rss_fetch
from tools.tavily_tool import tavily_search
from tools.wiki_tool import wiki_search

EXPECTED_KEYS = {"title", "url", "content", "source", "published"}


def _assert_article_shape(article: dict):
    assert set(article.keys()) == EXPECTED_KEYS, (
        f"Unexpected article shape: {sorted(article.keys())}"
    )


def run_tool_smoke_test():
    query = "feminism India"
    results = {
        "tavily": tavily_search(query),
        "wikipedia": [wiki_search(query)] if wiki_search(query) else [],
        "rss": rss_fetch(query),
        "duckduckgo": ddg_search(query),
    }

    for tool_name, items in results.items():
        print(f"{tool_name}: {len(items)} result(s)")
        if items:
            _assert_article_shape(items[0])
            print(f"  first title: {items[0]['title']}")
        else:
            print("  no results returned in current environment")


if __name__ == "__main__":
    run_tool_smoke_test()
