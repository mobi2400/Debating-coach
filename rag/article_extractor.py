from __future__ import annotations

import re


BOILERPLATE_SNIPPETS = (
    "cookie policy",
    "accept cookies",
    "subscribe to our newsletter",
    "sign up for our newsletter",
    "all rights reserved",
    "skip to content",
    "advertisement",
    "read more",
)


def _clean_line(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    return cleaned


def extract_article_text(soup) -> str:
    for tag_name in ("script", "style", "noscript", "svg", "footer", "nav", "aside", "form"):
        for node in soup.find_all(tag_name):
            node.decompose()

    candidates = []
    for selector in (
        "article",
        "main",
        "[role='main']",
        ".article-body",
        ".story-body",
        ".post-content",
        ".entry-content",
    ):
        try:
            candidates.extend(soup.select(selector))
        except Exception:
            continue

    blocks = candidates or [soup]
    seen: set[str] = set()
    paragraphs: list[str] = []

    for block in blocks:
        for node in block.find_all(["p", "li", "h1", "h2", "h3"]):
            text = _clean_line(node.get_text(" ", strip=True))
            if len(text) < 35:
                continue
            lowered = text.lower()
            if any(snippet in lowered for snippet in BOILERPLATE_SNIPPETS):
                continue
            signature = re.sub(r"[^a-z0-9]+", " ", lowered).strip()[:220]
            if not signature or signature in seen:
                continue
            seen.add(signature)
            paragraphs.append(text)

    if not paragraphs:
        text = _clean_line(soup.get_text(" ", strip=True))
        return text

    return "\n".join(paragraphs)
