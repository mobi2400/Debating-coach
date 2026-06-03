from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.english_coach_node import _extract_candidates, _heuristic_english_lesson


def run_english_test():
    rag_context = """
    session 4
    cred- means believe or trust.
    lucid means clear and easy to understand.
    cogent means clear, logical, and convincing.
    nuance means a subtle difference in meaning.
    """

    words, roots = _extract_candidates(rag_context)
    assert words, "Expected at least one extracted vocabulary word"
    assert roots, "Expected at least one extracted root"

    lesson, vocab_words, word_roots = _heuristic_english_lesson("geopolitics", rag_context)
    assert "ENGLISH POWER" in lesson
    assert "geopolitics" in lesson.lower()
    assert vocab_words
    assert word_roots
    print("English lesson checks passed.")


if __name__ == "__main__":
    run_english_test()
