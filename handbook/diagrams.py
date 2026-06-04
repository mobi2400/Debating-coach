"""Generators for every diagram we embed in the handbook PDF.

Each function returns a PIL Image (saved to disk via matplotlib) the caller
can pass to ReportLab's Image flowable. Diagrams use the same dark palette
as the surrounding pages so they read as part of the document.
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

PAGE_BG = "#0d1117"
PANEL_BG = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#7ee8fa"
ACCENT_2 = "#f0c674"
ACCENT_3 = "#a5e075"
WARN = "#ff7b72"
INFO = "#79c0ff"


def _figure(width_in: float, height_in: float):
    fig, ax = plt.subplots(figsize=(width_in, height_in), facecolor=PAGE_BG)
    ax.set_facecolor(PAGE_BG)
    ax.axis("off")
    return fig, ax


def _box(ax, x, y, w, h, label, *, fill=PANEL_BG, edge=ACCENT, text_color=TEXT, fontsize=9):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.2, edgecolor=edge, facecolor=fill,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            color=text_color, fontsize=fontsize, wrap=True)


def _arrow(ax, x1, y1, x2, y2, color=MUTED, lw=1.0, style="->"):
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=12,
        linewidth=lw, color=color,
    )
    ax.add_patch(arrow)


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=PAGE_BG, edgecolor="none")
    plt.close(fig)
    return path


# ------------------------------------------------------------- 1. system map
def system_map(out: Path) -> Path:
    fig, ax = _figure(9, 5.5)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)

    # Top: data sources
    _box(ax, 0.2, 5.0, 1.6, 0.7, "Tavily", edge=ACCENT)
    _box(ax, 2.0, 5.0, 1.6, 0.7, "Wikipedia", edge=ACCENT)
    _box(ax, 3.8, 5.0, 1.6, 0.7, "RSS", edge=ACCENT)
    _box(ax, 5.6, 5.0, 1.6, 0.7, "DuckDuckGo", edge=ACCENT)
    _box(ax, 7.4, 5.0, 2.3, 0.7, "FAISS vector stores", edge=ACCENT_2)

    # Middle: graph
    _box(ax, 0.6, 3.3, 8.8, 1.3,
         "LangGraph daily pipeline\nresearch → rag_enrich → filter → rank → summarize → argue → coach → english_coach → format",
         edge=ACCENT_3, fontsize=9)

    # Below: LLMs
    _box(ax, 0.6, 2.0, 2.0, 0.7, "Groq pool", edge=INFO)
    _box(ax, 2.8, 2.0, 2.0, 0.7, "Gemini", edge=INFO)
    _box(ax, 5.0, 2.0, 2.0, 0.7, "Prompt cache", edge=INFO)
    _box(ax, 7.2, 2.0, 2.2, 0.7, "Fallback proxy", edge=INFO)

    # Below: outputs
    _box(ax, 1.5, 0.6, 2.6, 0.8, "Telegram bot\n(daily digest)", edge=ACCENT_2)
    _box(ax, 4.3, 0.6, 2.6, 0.8, "weekly_log.json\n(compact memory)", edge=ACCENT_2)
    _box(ax, 7.1, 0.6, 2.3, 0.8, "GitHub Actions\nscheduler", edge=ACCENT_2)

    # Arrows
    for x in (1.0, 2.8, 4.6, 6.4):
        _arrow(ax, x, 5.0, x, 4.6)
    _arrow(ax, 8.5, 5.0, 8.5, 4.6)
    for x in (1.6, 3.8, 6.0, 8.3):
        _arrow(ax, x, 3.3, x, 2.7)
    _arrow(ax, 5.0, 2.0, 3.0, 1.4)
    _arrow(ax, 5.0, 2.0, 5.6, 1.4)
    _arrow(ax, 5.0, 2.0, 8.0, 1.4)

    return _save(fig, out)


# ------------------------------------------------------------- 2. agent state
def agent_state(out: Path) -> Path:
    fig, ax = _figure(8.5, 5.5)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)

    _box(ax, 3.0, 5.2, 4.0, 0.7, "AgentState (TypedDict)\nshared mutable dict", edge=ACCENT, fontsize=10)

    fields = [
        ("Input", ["topic", "selector_reason", "topic_info"]),
        ("Research", ["raw_articles", "reference_background"]),
        ("RAG", ["enriched_context"]),
        ("Rank", ["ranked_articles"]),
        ("Summarize", ["summaries", "key_facts", "concepts"]),
        ("Argue", ["arguments"]),
        ("Coach", ["debate_angle", "debate_packet"]),
        ("English", ["english_lesson", "vocab_words", "word_roots"]),
        ("Format", ["final_doc"]),
        ("Router/Night", ["task_type", "studied_today", "quiz_score"]),
    ]
    cols = 2
    col_w, row_h = 4.4, 0.4
    for i, (label, items) in enumerate(fields):
        col = i % cols
        row = i // cols
        x = 0.5 + col * (col_w + 0.4)
        y = 4.5 - row * (row_h + 0.05) - row * 0.18
        _box(ax, x, y, col_w, row_h,
             f"{label}: {', '.join(items)}",
             edge=BORDER, fill=PANEL_BG, fontsize=8)

    return _save(fig, out)


# ------------------------------------------------------------- 3. rag stores
def rag_stores(out: Path) -> Path:
    fig, ax = _figure(9, 4.5)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)

    stores = [
        ("knowledge_db", "Topic PDFs\nNews\nWikipedia", "Hybrid\n(BM25 40% + Vector 60%)", ACCENT),
        ("style_db",     "Your speeches\nDebate scripts\nNotes",       "Similarity\nthreshold 0.72",        ACCENT_2),
        ("reasoning_db", "Debate theory\nRhetoric\nYouTube",            "MMR\nλ=0.65, fetch_k=25",          ACCENT_3),
        ("english_db",   "Word Power\nMade Easy",                       "Similarity\nstructured metadata",  INFO),
    ]
    w = 2.1
    gap = 0.2
    start_x = 0.5
    for i, (name, content, mode, edge) in enumerate(stores):
        x = start_x + i * (w + gap)
        _box(ax, x, 3.3, w, 1.1, name, edge=edge, fontsize=11)
        _box(ax, x, 1.9, w, 1.2, content, edge=BORDER, fontsize=8)
        _box(ax, x, 0.4, w, 1.2, mode, edge=BORDER, fontsize=8)

    ax.text(5.0, 4.6, "Four lanes — different content, different retrieval",
            ha="center", color=MUTED, fontsize=10)
    return _save(fig, out)


# ------------------------------------------------------------- 4. flow chart of llm fallback
def llm_fallback(out: Path) -> Path:
    fig, ax = _figure(8, 5)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)

    _box(ax, 4.0, 5.2, 2.0, 0.6, "task_type", edge=ACCENT)
    _box(ax, 4.0, 4.3, 2.0, 0.6, "route_by_task", edge=ACCENT_2)

    chains = [
        ("best",       ["best", "reasoning", "balanced"]),
        ("reasoning",  ["reasoning", "balanced", "fast"]),
        ("structured", ["structured", "balanced", "fast"]),
    ]
    for i, (primary, fallback) in enumerate(chains):
        y = 3.2 - i * 1.0
        _box(ax, 0.4, y, 2.2, 0.6, primary, edge=INFO, fontsize=9)
        chain = " → ".join(fallback)
        _box(ax, 3.0, y, 6.5, 0.6, f"chain: {chain}", edge=BORDER, fontsize=9)

    _arrow(ax, 5.0, 5.2, 5.0, 4.9)
    _arrow(ax, 5.0, 4.3, 5.0, 4.0)
    ax.text(5.0, 0.3, "Each step retries only on real failure — no pre-flight ping.",
            ha="center", color=MUTED, fontsize=9)
    return _save(fig, out)


# ------------------------------------------------------------- 5. daily pipeline detail
def daily_pipeline(out: Path) -> Path:
    fig, ax = _figure(9.5, 6.0)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)

    steps = [
        ("research",       "Tavily + Wiki + RSS + DDG (parallel)", ACCENT),
        ("rag_enrich",     "FAISS retrieval into enriched_context", ACCENT_3),
        ("filter",         "LLM/heuristic drop low-value items",    ACCENT_2),
        ("rank",           "Promote news, penalise reference",      ACCENT_2),
        ("summarize",      "Per-article SUMMARY / KEY FACT / CONCEPT", ACCENT),
        ("argue",          "3 FOR / 3 AGAINST / 1 MIDDLE",          ACCENT),
        ("coach",          "Debate packet (unique angle ... judge lang)", ACCENT),
        ("english_coach",  "Word Power Made Easy lesson",           INFO),
        ("format",         "9-section Telegram-ready digest",       ACCENT_2),
    ]
    for i, (name, desc, color) in enumerate(steps):
        y = 6.2 - i * 0.65
        _box(ax, 0.4, y, 2.2, 0.5, name, edge=color, fontsize=10)
        _box(ax, 2.8, y, 7.8, 0.5, desc, edge=BORDER, fontsize=9)
        if i < len(steps) - 1:
            _arrow(ax, 1.5, y, 1.5, y - 0.15)

    return _save(fig, out)


# ------------------------------------------------------------- 6. github actions cycle
def actions_cycle(out: Path) -> Path:
    fig, ax = _figure(9, 4.5)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)

    steps = [
        (1.0, 3.7, "Cron fires"),
        (3.0, 3.7, "Checkout"),
        (5.0, 3.7, "Restore FAISS cache"),
        (7.0, 3.7, "Rebuild if miss"),
        (9.0, 3.7, "main.py runs"),
        (9.0, 2.0, "Send via Telegram"),
        (7.0, 2.0, "Update log"),
        (5.0, 2.0, "Commit log back"),
        (3.0, 2.0, "Push"),
        (1.0, 2.0, "Cache saved"),
    ]
    for x, y, label in steps:
        _box(ax, x - 0.8, y - 0.3, 1.7, 0.6, label, edge=ACCENT_2, fontsize=8)

    for i in range(len(steps) - 1):
        x1, y1, _ = steps[i]
        x2, y2, _ = steps[i + 1]
        _arrow(ax, x1, y1 - 0.32 if y1 == y2 else y1, x2, y2)

    ax.text(5, 0.5, "Stateful loop: cache + log persist between runs",
            ha="center", color=MUTED, fontsize=10)
    return _save(fig, out)


# ------------------------------------------------------------- 7. bug bar (anatomy)
def bug_anatomy(out: Path) -> Path:
    fig, ax = _figure(9, 4)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)

    quadrants = [
        (0.3, 2.2, "SYMPTOM",       "What you see in the wild",       WARN),
        (5.2, 2.2, "ROOT CAUSE",    "What is actually wrong",         ACCENT_2),
        (0.3, 0.4, "FIX",           "Smallest correct change",        ACCENT_3),
        (5.2, 0.4, "LESSON",        "What you'll keep doing forever", INFO),
    ]
    for x, y, title, sub, color in quadrants:
        _box(ax, x, y, 4.5, 1.5, f"{title}\n\n{sub}", edge=color, fontsize=10)

    return _save(fig, out)


def render_all(out_dir: Path) -> dict[str, Path]:
    return {
        "system_map":      system_map(out_dir / "system_map.png"),
        "agent_state":     agent_state(out_dir / "agent_state.png"),
        "rag_stores":      rag_stores(out_dir / "rag_stores.png"),
        "llm_fallback":    llm_fallback(out_dir / "llm_fallback.png"),
        "daily_pipeline":  daily_pipeline(out_dir / "daily_pipeline.png"),
        "actions_cycle":   actions_cycle(out_dir / "actions_cycle.png"),
        "bug_anatomy":     bug_anatomy(out_dir / "bug_anatomy.png"),
    }


if __name__ == "__main__":
    paths = render_all(Path(__file__).parent / "_assets")
    for k, v in paths.items():
        print(f"{k:18s} -> {v}")
