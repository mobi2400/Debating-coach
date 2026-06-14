from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bs4 import BeautifulSoup

from rag.article_extractor import extract_article_text


def test_extract_article_text_removes_boilerplate_and_duplicates():
    html = """
    <html>
      <body>
        <nav>Subscribe to our newsletter</nav>
        <article>
          <h1>Why sanctions matter in geopolitics</h1>
          <p>Sanctions shape bargaining power between states and change strategic incentives over time.</p>
          <p>Sanctions shape bargaining power between states and change strategic incentives over time.</p>
          <p>Decision-makers must compare immediate coercion gains against long-term escalation risks.</p>
        </article>
        <footer>All rights reserved</footer>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")

    text = extract_article_text(soup)

    assert "Subscribe to our newsletter" not in text
    assert text.count("Sanctions shape bargaining power") == 1
    assert "Decision-makers must compare" in text
