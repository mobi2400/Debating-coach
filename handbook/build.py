"""Build the DebateIQ learning handbook PDF.

Run: python handbook/build.py
Output: handbook/DebateIQ_Handbook.pdf
"""

from __future__ import annotations

import html
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from handbook.diagrams import render_all
from handbook.style import (
    ACCENT,
    ACCENT_2,
    BOTTOM,
    LEFT,
    MUTED,
    PAGE_BG,
    PAGE_H,
    PAGE_W,
    RIGHT,
    TEXT,
    TOP,
    build_styles,
)

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "_assets"
OUT = ROOT / "DebateIQ_Handbook.pdf"

STYLES = build_styles()


# ---------------------------------------------------------------- helpers
def P(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def code(text: str) -> Paragraph:
    # ReportLab Paragraph respects basic XML tags; escape user text first.
    escaped = html.escape(text).replace("\n", "<br/>")
    return Paragraph(f'<font face="Courier" size="9">{escaped}</font>', STYLES["Code"])


def callout(title: str, body: str, kind: str = "Callout") -> Paragraph:
    style_name = {"info": "Tip", "warn": "Warning", "tip": "Tip"}.get(kind, "Callout")
    return Paragraph(f"<b>{html.escape(title)}</b><br/>{body}", STYLES[style_name])


def term(label: str, gloss: str) -> str:
    """Returns the inline HTML for a buzzword + its short gloss.

    Use in body paragraphs the first time a term appears, like:
        f"... we use {term('RAG', 'pull your own material into the prompt')} ..."

    The label is bolded; the gloss is italicised in a warm brown.
    """
    return (
        f'<b>{html.escape(label)}</b> '
        f'<i><font color="#6e4a18">({html.escape(gloss)})</font></i>'
    )


def buzz(label: str, body: str) -> Paragraph:
    """A dedicated 'buzzword check' paragraph — used when a term needs more
    than a one-line gloss. Renders as a small indented italic note."""
    return Paragraph(
        f'<b><font color="#6e4a18">{html.escape(label)}.</font></b> {body}',
        STYLES["Buzz"],
    )


def lead(text: str) -> Paragraph:
    """A one-line summary that sits under a chapter title."""
    return Paragraph(text, STYLES["ChapterLead"])


def bullets(items: list[str]):
    """Render bullets as a single KeepTogether flowable. Each line gets an
    inline coloured marker; KeepTogether tries to avoid splitting the list
    across pages when it would look ugly."""
    rows = [
        Paragraph(
            f'<font color="#f0c674" size="11">●</font>&nbsp;&nbsp;{item}',
            STYLES["Bullet"],
        )
        for item in items
    ]
    return KeepTogether(rows)


def chapter(num: int, title: str) -> list:
    return [
        Spacer(1, 6 * mm),
        P(f"Chapter {num}", "ChapterNumber"),
        P(title, "ChapterTitle"),
    ]


def section(title: str) -> Paragraph:
    return P(title, "SectionTitle")


def subsection(title: str) -> Paragraph:
    return P(title, "SubSection")


def image_block(path: Path, width_mm: float = 150, caption: str | None = None) -> list:
    items: list = []
    if path.exists():
        img = Image(str(path), width=width_mm * mm, height=(width_mm * 0.6) * mm,
                    kind="proportional")
        items.append(img)
    if caption:
        items.append(P(caption, "Caption"))
    return items


# ---------------------------------------------------------------- page template
def _draw_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAGE_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Footer
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(LEFT, BOTTOM / 2,
                      "DebateIQ Learning Handbook")
    canvas.drawRightString(PAGE_W - RIGHT, BOTTOM / 2,
                           f"{doc.page}")
    canvas.restoreState()


def _draw_cover_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAGE_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(0.4)
    canvas.line(LEFT, PAGE_H - TOP - 5, PAGE_W - RIGHT, PAGE_H - TOP - 5)
    canvas.line(LEFT, BOTTOM + 5, PAGE_W - RIGHT, BOTTOM + 5)
    canvas.restoreState()


# ---------------------------------------------------------------- content
def cover() -> list:
    return [
        Spacer(1, 60 * mm),
        P("DebateIQ", "CoverTitle"),
        P("A learning handbook for the developer who wrote the code with AI<br/>"
          "and now wants to own every line of it.", "CoverSubtitle"),
        Spacer(1, 40 * mm),
        P("Architecture · Agentic AI · RAG · Tooling · Automation", "CoverMuted"),
        Spacer(1, 4 * mm),
        P("Bugs we hit, why they happened, and the lesson behind each fix", "CoverMuted"),
    ]


def how_to_read() -> list:
    body = [
        *chapter(0, "Foreword: how to read this book"),
        lead("Written for the developer who built this project with an AI helper "
             "and now wants to own every line of it without that helper."),
        P("Every concept is introduced before it's used. Every design choice has "
          "a short rationale. Every bug we fixed has a paragraph explaining what "
          "broke and why. The first time a piece of jargon appears in the body "
          "text, you'll see it followed by a short italic gloss like this — "
          f"{term('RAG', 'pulling your own material into the model prompt')} — so "
          "you never have to stop and Google."),
        section("How chapters are organised"),
        bullets([
            "Each chapter starts with what the topic is in plain language.",
            "Then why this project needed it.",
            "Then how it's wired in the codebase (with file paths).",
            "Then a small code snippet — never a whole file, only the key idea.",
            "Then gotchas: things that will bite you if you change it.",
        ]),
        section("Conventions used in this book"),
        callout("Callout — concept",
                "A boxed idea worth committing to memory."),
        callout("Tip — practical move",
                "A way of working that will save you debugging time later.",
                kind="tip"),
        callout("Warning — common pitfall",
                "Something that has actually broken on this project in the past.",
                kind="warn"),
        buzz("Buzzword check",
             "An italic note like this appears when a term needs more space than "
             "an inline gloss. If you can already define the word, skim past."),
        section("The mental model in one sentence"),
        P("DebateIQ <b>picks one topic per day</b>, <b>researches</b> it through "
          "public sources and a private knowledge base, <b>builds a debate lesson</b> "
          "around it, <b>delivers</b> the lesson on Telegram, and then "
          "<b>reinforces</b> it the same night and at the end of the week."),
    ]
    return body


def chapter_big_picture(assets: dict) -> list:
    return [
        PageBreak(),
        *chapter(1, "The big picture"),
        lead("Before any code, hold the system map in your head. Every file we "
             "talk about later sits in one of those boxes."),
        Spacer(1, 4 * mm),
        *image_block(assets["system_map"], width_mm=150,
                     caption="DebateIQ at a glance — sources at the top, a LangGraph pipeline in the middle, providers below it, outputs at the bottom."),
        section("What problem the project solves"),
        P("A serious debater needs to know what's happening in the world today, "
          "what frameworks apply to it, what their best version of both sides looks "
          "like, and what specific language they should be using. Doing that by hand "
          "every morning eats two hours. DebateIQ does it on a schedule, in five "
          "minutes of compute, and delivers the result on Telegram."),
        section("Four loops that the system runs"),
        bullets([
            "<b>Daily loop</b> — pulls fresh material on one topic and turns it into a structured lesson.",
            "<b>Night loop</b> — quizzes you on what you actually retained, or sends a compressed bedtime recap.",
            "<b>Weekend loop</b> — reads the whole week's memory and extracts only the concepts worth keeping.",
            "<b>Ingestion loop</b> — runs once when you add a PDF/site/video, builds the FAISS indexes.",
        ]),
        section("The biggest architectural decision"),
        callout("One topic per day, not many",
                "An earlier version of this codebase tried to cover several topics "
                "every morning. The output was unreadable and the LLM token cost "
                "was unbounded. The current design picks exactly one priority topic "
                "per day using a lightweight spaced-repetition heuristic. Every "
                "downstream module is shaped by that choice — keep this in mind."),
    ]


def chapter_folder_structure_intro():
    return lead("If a stranger walked into this codebase, the folder layout "
                "tells them what we thought were the important boundaries.")


def chapter_folder_structure() -> list:
    tree = """\
Debate Coach/
├── .github/workflows/        ← Automation (CI + scheduler)
├── agents/                   ← One file per pipeline node
│   ├── research_node.py
│   ├── rag_enrich_node.py
│   ├── filter_node.py
│   ├── rank_node.py
│   ├── summarize_node.py
│   ├── argue_node.py
│   ├── coach_node.py
│   ├── english_coach_node.py
│   ├── english_quiz_node.py
│   ├── format_node.py
│   ├── night_agent.py
│   ├── weekend_agent.py
│   └── topic_selector.py
├── core/                     ← Shared plumbing
│   ├── state.py              ← AgentState TypedDict
│   ├── llm_pool.py           ← Model definitions
│   ├── llm_router.py         ← task_type → model key
│   ├── fallback.py           ← Fallback proxy
│   ├── prompt_cache.py       ← Disk-backed LLM cache
│   ├── topic_utils.py        ← topic_name(), search query expansion
│   └── network_utils.py      ← Proxy env scrubber
├── delivery/                 ← Output adapters
│   ├── telegram.py           ← Live
│   └── whatsapp.py           ← Shim for old imports
├── rag/                      ← Retrieval-augmented generation
│   ├── chunking_strategy.py
│   ├── embeddings.py
│   ├── ingest.py
│   ├── retrieval_pipeline.py
│   ├── wpm_extractor.py
│   └── sources.json
├── memory/                   ← Persistent state
│   ├── weekly_store.py
│   └── weekly_log.json
├── tools/                    ← External research adapters
│   ├── tavily_tool.py
│   ├── wiki_tool.py
│   ├── rss_tool.py
│   └── ddg_tool.py
├── knowledge_base/pdfs/      ← Source material you upload
├── faiss/                    ← Built vector indexes (gitignored)
├── tests/                    ← Smoke + e2e tests
├── graph.py                  ← LangGraph wiring (3 graphs)
├── main.py                   ← Entry point
├── topics.json               ← Priority topics + study lens
├── requirements.txt
└── .env                      ← Secrets (gitignored)
"""
    return [
        PageBreak(),
        *chapter(2, "The folder structure"),
        chapter_folder_structure_intro(),
        P("Here is ours, and why each directory exists. The dark blocks below "
          "are file paths; the comments after each one are the role that "
          "directory plays."),
        code(tree),
        section("Why agents/ is its own folder"),
        P("Every node in the LangGraph pipeline is a pure function: it takes the "
          "shared <b>AgentState</b> dict, does its work, and returns the same dict "
          "with new fields filled in. By giving each node its own file we get three "
          "things for free: each node is easy to test in isolation, you can read the "
          "whole pipeline by reading the file names in order, and replacing a node "
          "(say, swapping the rank logic) means editing exactly one file."),
        section("Why core/ holds plumbing, not behaviour"),
        P("Anything that more than one agent needs lives in <b>core/</b>. State, "
          "model pool, router, fallback, prompt cache, topic utilities, network "
          "scrubbing. Agents import from core; core never imports from agents. That "
          "one rule prevents circular imports and keeps reasoning about dependencies "
          "linear."),
        section("Why delivery/ is separate from agents/"),
        P("Delivery is an I/O concern, not a thinking concern. We've already "
          "migrated delivery three times (Twilio → Meta Cloud → Telegram). Each time "
          "we only had to touch <b>delivery/</b>, never the pipeline nodes. That's "
          "what a clean boundary buys you."),
        section("Why rag/ and tools/ are separate"),
        P("<b>tools/</b> is for <i>live</i> data — calls go to the public internet "
          "every time. <b>rag/</b> is for <i>indexed</i> data — material you "
          "uploaded once and now retrieve by similarity. They behave very "
          "differently under failure (a live tool 429s, an index file simply isn't "
          "there) so we keep them apart."),
        section("Why memory/ is plain JSON, not a database"),
        P("The whole point of memory in this project is to compound, not to scale. "
          "A 50KB JSON file holds a year of daily entries; SQLite would be overkill. "
          "Plain JSON also lets the GitHub Actions runner commit memory back to the "
          "repo trivially, which is how the night and weekend agents see history "
          "between runs."),
        callout("Lesson — folders are architecture",
                "If you can't tell what a directory is for from its name, the "
                "architecture has a leak. Resist the urge to create a misc/ or "
                "utils/ bag-of-junk folder."),
    ]


def chapter_prereqs() -> list:
    return [
        PageBreak(),
        *chapter(3, "Foundations you need before reading further"),
        lead("Concepts the rest of the book quietly assumes you already know. "
             "If any of these feel new, stop here and learn them first."),
        section("Python project basics"),
        bullets([
            f"{term('Virtual environment', 'isolated Python install per project so libraries do not collide')} — every project gets its own. We use <b>uv</b> because it resolves dependencies in one shot.",
            "<b>requirements.txt</b> — a pinned list of every package we need. Lower bounds (>=) for flexibility, exact pins only when a version is known to break.",
            f"{term('Type hints', 'function signatures that tell the editor what types are expected')} — <i>def f(state: dict) -&gt; dict</i> is documentation the editor checks for you.",
            "<b>__init__.py</b> — an empty file telling Python this folder is an importable package. Every folder you import from needs one.",
        ]),
        buzz("uv",
             "A drop-in replacement for pip written in Rust. Installs a 50-package "
             "project in seconds instead of minutes. The command is <i>uv pip install …</i>."),
        section("Environment variables and secrets"),
        P("Anything sensitive — API keys, bot tokens, your phone number — lives in "
          f"a <b>.env</b> file at the project root. {term('.env file', 'a plain-text file holding key=value pairs the program reads at startup')} "
          "It's listed in <b>.gitignore</b> so it never reaches the public repo."),
        P(f"In production those same values come from {term('GitHub Actions Secrets', 'encrypted values stored in your GitHub repo, available to workflows as env vars')}. "
          "The code reads either source via <i>os.getenv()</i> and never cares which one it's talking to."),
        callout("Tip — read env vars lazily",
                "Don't read .env at module import. Read it inside the function "
                "that actually needs it. We had a real bug where DEV_MODE was "
                "captured at import time, then later toggled, and the change "
                "had no effect.",
                kind="tip"),
        section("Git and GitHub"),
        bullets([
            "<b>git add / commit / push</b> are the three commands you'll run hundreds of times.",
            "Every meaningful change becomes one commit with a present-tense message: <i>fix: drop pre-flight ping from fallback proxy</i>.",
            f"{term('GitHub Actions', 'GitHub built-in automation — runs scripts when you push, on a schedule, or manually')} runs our scheduler and tests. Broken CI blocks shipping.",
        ]),
        buzz("CI / CD",
             "<i>Continuous Integration</i> means tests run on every push so "
             "regressions surface immediately. <i>Continuous Deployment</i> "
             "means the same automation also ships the change. Our CI runs "
             "tests; our scheduler is closer to a cron job than true CD."),
        section("LangChain and LangGraph in one paragraph each"),
        P(f"{term('LangChain', 'a Python library that wraps every LLM provider behind one common interface')} is glue. "
          "Your code calls <i>llm.invoke(prompt)</i> and stops caring whether the "
          "provider behind it is Groq, OpenAI, or Gemini. We use a tiny slice — "
          "the chat-model wrappers and the vector-store retriever interface — and "
          "write everything else ourselves."),
        P(f"{term('LangGraph', 'a workflow engine built on top of LangChain')} lets you declare "
          "<b>nodes</b> (functions that take state and return state) and "
          "<b>edges</b> (which node feeds which). The library handles the running "
          "order. The alternative — manually orchestrating nine functions and "
          "their failure modes — is fragile."),
        buzz("LLM",
             "<i>Large Language Model</i>. A neural network trained to predict the "
             "next token of text. ChatGPT, Claude, Gemini, Llama, Qwen are all LLMs. "
             "When this book says 'the model', it means an LLM."),
    ]


def chapter_agent_state(assets: dict) -> list:
    return [
        PageBreak(),
        *chapter(4, "Agentic AI in this project, demystified"),
        lead("'Agentic AI' sounds mystical. In this codebase it means: ordinary "
             "Python functions sharing one dictionary, run in a defined order."),
        buzz("Agentic AI",
             "Marketing term for systems where an LLM (or a set of them) makes "
             "decisions in a loop — read inputs, decide what to do, take an action, "
             "read the result, repeat. We use a milder version: the LLM doesn't "
             "decide the flow, but each step uses an LLM to do its work."),
        P(f"Before {term('LangGraph', 'workflow engine that runs your nodes in order')}, "
          "a Python program is a chain of function calls. After LangGraph, a Python "
          "program is still a chain of function calls — the only change is that the "
          "data passed between them lives in one shared, mutable dictionary. That "
          "dictionary is the <b>agent state</b>. Every node reads from it and writes "
          "back to it. Nothing else moves between nodes."),
        Spacer(1, 4 * mm),
        *image_block(assets["agent_state"], width_mm=150,
                     caption="AgentState fields, grouped by which pipeline phase populates them."),
        section("Reading the state contract"),
        P(f"Open <i>core/state.py</i>. The <b>AgentState</b> {term('TypedDict', 'a Python dictionary type with declared keys and value types — gives you editor warnings if you mistype')} "
          "is the contract between every node. If a node needs a new field — say, "
          "<i>english_quiz_score</i> — you add it here first, then every node knows "
          "it exists. If a field disappears from this file, the editor immediately "
          "tells you which nodes still reference it."),
        section("What an agent really is"),
        P("In this codebase an <i>agent</i> is just <b>a function that takes "
          "AgentState and returns AgentState</b>. There's no magic. The word "
          "'agent' is used because the function decides what to do next based on "
          "the state — for example, the night agent reads <i>studied_today</i> and "
          "picks between quiz mode and bedtime mode."),
        code("def example_node(state: dict) -> dict:\n"
             "    # Read whatever inputs you need\n"
             "    topic = state['topic']\n\n"
             "    # Do work — LLM call, RAG lookup, computation\n"
             "    result = some_work(topic)\n\n"
             "    # Write outputs back to the same dict\n"
             "    state['my_new_field'] = result\n"
             "    return state"),
        section("Why mutate, not return a new dict"),
        P("Both are valid patterns. We mutate because LangGraph treats the state "
          "as a passing baton, not a copy. Mutating means every node sees every "
          "previous node's output without explicit plumbing."),
        callout("Warning — never crash a node silently",
                "If a node can't produce its output (LLM 429, retrieval empty, "
                "network down), it must still leave the field populated — usually "
                "with a heuristic fallback. A missing field will crash the next "
                "node in the chain.",
                kind="warn"),
        section("The graph itself"),
        P("Open <i>graph.py</i>. It declares three graphs — daily, night, weekend "
          "— by adding nodes to a <i>StateGraph</i> and drawing edges between them. "
          "For the daily graph the edges form a straight line; for the night graph "
          "it's a single node that branches at runtime based on your reply on "
          "Telegram."),
        code("graph = StateGraph(AgentState)\n"
             "graph.add_node('research', research_node)\n"
             "graph.add_node('rag_enrich', rag_enrich_node)\n"
             "graph.add_edge('research', 'rag_enrich')\n"
             "graph.set_entry_point('research')\n"
             "compiled = graph.compile()"),
        callout("Lesson — graphs document themselves",
                "If you can't draw your project on a whiteboard with arrows, your "
                "control flow is too tangled. Forcing the pipeline into a graph "
                "made every later bug easy to localise."),
    ]


def chapter_llm_layer(assets: dict) -> list:
    return [
        PageBreak(),
        *chapter(5, "The LLM layer"),
        lead("Two ideas tame the most unreliable part of the system: don't use "
             "your biggest model for trivial work, and have a backup plan when "
             "the primary one rejects you."),
        P(f"Large language models are the most expensive and most unreliable part "
          "of the system. Two patterns tame both: <b>role-based routing</b> — "
          "don't use your biggest model for trivial work — and "
          f"{term('fallback chains', 'an ordered list of models to try when the primary one fails')} — when the primary "
          f"{term('429s', 'HTTP status code 429 means the provider rate-limited you (too many requests or tokens)')}, drop down to the next tier instead of failing the whole node."),
        section("The model pool"),
        P("<i>core/llm_pool.py</i> holds the only place where a model is "
          "instantiated. Everywhere else asks for a model by <i>role</i>, never by "
          "name. That indirection means migrating from one provider to another "
          "is a one-file change."),
        code("LLM_POOL = {\n"
             "    'fast'      : llama-3.1-8b-instant,   # cheap cleanup\n"
             "    'balanced'  : llama-3.3-70b-versatile, # summaries\n"
             "    'structured': openai/gpt-oss-20b,      # JSON outputs\n"
             "    'reasoning' : qwen/qwen3-32b,          # arguments\n"
             "    'long_ctx'  : gemini-2.5-flash,        # long reads\n"
             "    'best'      : openai/gpt-oss-120b,     # coach\n"
             "}"),
        section("Why six lanes, not one"),
        bullets([
            "<b>fast</b> handles filter + rank — yes/no decisions, no nuance needed.",
            "<b>balanced</b> handles summaries and bedtime — quality matters, but a 70B model is enough.",
            "<b>structured</b> handles JSON shapes (quiz, format). A model trained for instruction-following is more reliable here than a bigger creative model.",
            "<b>reasoning</b> handles argument generation. We want chain-of-thought, even visible thinking traces.",
            "<b>long_ctx</b> only fires when an article is huge — Gemini's million-token context shines here.",
            "<b>best</b> is reserved for the coach output, where one mediocre paragraph ruins the whole digest.",
        ]),
        section("Routing: task_type → model key"),
        P("Every node sets <b>state['task_type']</b> before calling the LLM. "
          "<i>core/llm_router.py</i> turns that string into a model key. There's a "
          "special override: if an article is longer than ~8000 chars, we force the "
          "long_ctx lane regardless of task_type."),
        section("Fallback as a transparent proxy"),
        Spacer(1, 2 * mm),
        *image_block(assets["llm_fallback"], width_mm=150,
                     caption="get_llm_with_fallback returns a proxy. When the primary fails, the proxy walks down the chain."),
        P("<i>core/fallback.py</i> doesn't return the LLM directly. It returns a "
          "tiny proxy class that holds an ordered list of candidates. The proxy's "
          "<i>.invoke(prompt)</i> tries the first candidate; on any exception "
          "(rate limit, network, model decommissioned) it falls through to the "
          "next."),
        callout("Bug we fixed — the pre-flight ping",
                "The first version of the fallback proxy called <i>llm.invoke('ping')</i> "
                "before returning the model. That looked like good defensive "
                "engineering and was actively bad: it doubled token cost (every "
                "node burned an extra round trip) without actually predicting "
                "rate limits. We removed it; failures now surface on the real call.",
                kind="warn"),
        section("The disk cache that saves quota"),
        P(f"Free-tier providers cap your daily and per-minute tokens "
          f"({term('TPD/TPM', 'tokens per day / tokens per minute — provider-imposed quotas')}). "
          "The same topic comes up every ~14 days in our rotation, so the same "
          "prompts re-appear. <i>core/prompt_cache.py</i> hashes (scope, model, prompt) "
          "into a filename in <i>.cache/llm/</i>, stores the response for 30 days, "
          "and skips the network on a hit."),
        buzz("Cache hit / miss",
             "A <b>cache hit</b> means we found a stored answer for this exact "
             "prompt — return it free. A <b>cache miss</b> means we have to ask "
             "the model. The hit rate is the percentage of calls served from cache."),
        code("# wrap the LLM call:\n"
             "response = cached_invoke(llm, prompt, scope='summarize')"),
        callout("Tip — choose your cache scope deliberately",
                "The scope string is part of the cache key. <i>scope='argue'</i> and "
                "<i>scope='summarize'</i> never collide even if their prompts happen "
                "to match. Use one scope per node.",
                kind="tip"),
    ]


def chapter_research_tools() -> list:
    return [
        PageBreak(),
        *chapter(6, "Research tools — the live data layer"),
        lead("Four ways of asking the public internet for material on today's "
             "topic. Layered on purpose so one tool's blind spot is another's strength."),
        P("Four tools pull material from the public internet. Each one has a "
          "specific job; together they cover recency, depth, background, and "
          "redundancy."),
        buzz("API",
             "<i>Application Programming Interface</i> — a contract a service "
             "exposes so other programs can talk to it. Tavily's API takes a "
             "search query and returns articles."),
        section("Tavily — depth"),
        P("Tavily is a search API tuned for LLM input. It returns full article "
          "content, not just snippets. We use it as our primary deep-search lane."),
        code("from langchain_tavily import TavilySearch\nclient = TavilySearch(max_results=5, search_depth='advanced')"),
        section("Wikipedia — background"),
        P("For any topic, Wikipedia gives you the canonical definition and a "
          "history. We never lead a digest with Wikipedia content (it reads as "
          "filler), but the rank node uses it for the BACKGROUND section."),
        section("RSS — recency"),
        P(f"Fast-changing topics deserve a check on the last 24 hours of news. "
          f"{term('RSS', 'Really Simple Syndication — an XML feed publishers expose listing their newest items')} feeds "
          "expose a publisher's latest items as a machine-readable list. "
          "<i>tools/rss_tool.py</i> reads a handful of curated feeds (BBC, Al "
          "Jazeera, Reuters, The Hindu, Indian Express) and filters by topic keyword."),
        section("DuckDuckGo — redundancy"),
        P("No API key, no rate limits, low quality. It catches things the other "
          "three miss. Treat its results with suspicion."),
        section("Why we run them in parallel"),
        P(f"Four serial tool calls would add ~12 seconds of latency. "
          f"<i>research_node.py</i> runs them under a "
          f"{term('ThreadPoolExecutor', 'Python helper that runs multiple functions at once on separate threads')} "
          "with a 20-second global timeout. Whoever finishes first gets included; "
          "stragglers are dropped silently."),
        buzz("Parallel vs concurrent",
             "<b>Parallel</b> means truly at the same time on separate CPU cores. "
             "<b>Concurrent</b> means interleaved on one core. For network calls "
             "the distinction barely matters — your program is waiting on the "
             "network either way, so we get the speedup."),
        callout("Bug we fixed — broken proxy env vars",
                "On one machine every tool was returning empty. The diagnosis took "
                "an hour because the symptom looked like a code bug but the actual "
                "cause was HTTP_PROXY=http://127.0.0.1:9 lingering in the shell env "
                "from a previous experiment. We now scrub local proxy env vars at "
                "startup via core/network_utils.py.",
                kind="warn"),
        section("Why each tool normalises its output"),
        P("Each adapter returns dicts with the same keys: <i>title, url, content, "
          "source, published</i>. Downstream nodes don't care which provider the "
          "article came from. If you add a fifth tool tomorrow, mirror that shape."),
    ]


def chapter_rag(assets: dict) -> list:
    return [
        PageBreak(),
        *chapter(7, "RAG — retrieval-augmented generation"),
        lead("The trick that turns a general LLM into one that knows your "
             "specific PDFs, speeches, and notes."),
        buzz("RAG",
             "<i>Retrieval-Augmented Generation</i>. You don't fine-tune the model "
             "on your data. You search your data at query time, paste the most "
             "relevant chunks into the prompt, and let the model answer using them. "
             "Cheaper, faster, and easier to update than fine-tuning."),
        P("The mechanism is simple in three steps. (1) Take every document you "
          f"care about and split it into small pieces — {term('chunks', 'short slices of a document — typically 200-700 characters — small enough to embed cleanly')}. "
          f"(2) Convert each chunk into a high-dimensional number array — an "
          f"{term('embedding', 'a list of ~3000 numbers that represents the meaning of the text')}. "
          f"(3) Store the embeddings in a {term('vector store', 'a database optimised for finding the closest numerical neighbours to a query vector')} so "
          "you can retrieve the closest chunks to any new question."),
        section("The four vector stores"),
        Spacer(1, 2 * mm),
        *image_block(assets["rag_stores"], width_mm=150,
                     caption="Each lane has different content and a different retrieval style. Not one bag of knowledge."),
        section("Hybrid retrieval — BM25 + vectors"),
        P(f"Pure vector search is great for concepts and bad for exact terms. "
          "Searching <i>CEDAW</i> with embeddings might miss the chunk that has "
          f"those exact letters. {term('BM25', 'a classic keyword-ranking algorithm from the search-engine world — predates embeddings')} does the opposite. "
          "We combine them on the knowledge store with a 40/60 weight so both win."),
        buzz("Hybrid retrieval",
             "Run BM25 and vector search side by side, then blend their results. "
             "BM25 wins on exact terms (acronyms, proper nouns). Vectors win on "
             "concepts (paraphrases, synonyms). Together they cover both."),
        section("MMR — diverse chunks"),
        P(f"{term('MMR', 'Maximum Marginal Relevance — a retrieval style that penalises redundancy in the result set')} "
          "penalises chunks that overlap with chunks already chosen. Without it, "
          "asking the reasoning store about 'fairness' might pull five chunks that "
          "all argue the same point. With MMR you get five chunks that argue five "
          "different angles. Critical for the argue node, where variety matters."),
        section("Chunking is not cosmetic"),
        P("How you cut a PDF into pieces controls what retrieval can find. We use "
          "different chunkers per content type:"),
        bullets([
            "<b>News and topic PDFs</b>: 600 chars, sentence-aware splitter. Facts need surrounding context.",
            "<b>Your speeches</b>: 400 chars. One argument point per chunk.",
            "<b>Debate theory</b>: 720 chars, larger overlap. Arguments span multiple sentences.",
            "<b>YouTube transcripts</b>: 300 chars, word-boundary. Transcripts have no punctuation structure.",
            "<b>Word Power Made Easy</b>: 260 chars, semicolon-aware. Each vocabulary entry stays whole.",
        ]),
        section("Embeddings"),
        P("We use Google's <b>gemini-embedding-001</b> (3072-dim) for every "
          "store. The earlier version used three different sentence-transformer "
          "models; we collapsed them when torch wouldn't load reliably on Windows. "
          "Single embedding model means one API surface and one cost line."),
        section("FAISS, not Chroma"),
        P(f"{term('Chroma', 'a popular open-source vector database with a richer feature set than FAISS')} is more featureful "
          f"but had build issues on Windows and the version we needed "
          f"{term('segfaulted', 'crashed with a Segmentation Fault — a low-level memory error in native code')} "
          "under our query load. "
          f"{term('FAISS', 'Facebook AI Similarity Search — a small, fast library for nearest-neighbour search in vector spaces')} "
          "is leaner, loads in milliseconds, and persists as two flat files per "
          "store. Migration lived in commit <i>a00393f</i>. Lesson: pick the "
          "simpler local persistence layer unless you need the heavier semantics."),
        section("The Word Power Made Easy extractor"),
        P("That PDF has 47 numbered sessions with named subsections — <i>TEASER "
          "PREVIEW, USING THE WORDS, ORIGINS AND RELATED WORDS, REVIEW OF "
          "ETYMOLOGY</i>. Generic chunking flattens all of that and embeds drill "
          "exercises alongside teaching prose. <i>rag/wpm_extractor.py</i> splits "
          "by session, then by subsection, and tags each chunk with metadata "
          "(session number, section type). The english quiz can then ask for "
          "etymology chunks specifically."),
        callout("Lesson — RAG quality is 80% chunking",
                "We tuned models, distance metrics, and k-values for weeks before "
                "realising the actual problem was that we were chunking a dictionary "
                "book the same way we chunk news articles. Fix the chunker first."),
    ]


def chapter_pipeline(assets: dict) -> list:
    return [
        PageBreak(),
        *chapter(8, "The daily pipeline — node by node"),
        lead("The reference chapter. Come back here whenever you change a node "
             "or add a new one."),
        P("Each section names the file, what it reads from state, what it "
          "writes, and what its fallback does when the LLM fails."),
        Spacer(1, 4 * mm),
        *image_block(assets["daily_pipeline"], width_mm=150,
                     caption="The nine-step daily graph. Reads top-to-bottom, no branches."),
        section("research_node — gather raw material"),
        P("<b>Reads:</b> topic, topic_info. "
          "<b>Writes:</b> raw_articles, article_length. "
          "Fires Tavily + Wikipedia + RSS + DuckDuckGo in parallel under a 20s "
          "timeout. Empty input from a single tool is normal; empty input from all "
          "four means the topic is broken or the network is down."),
        section("rag_enrich_node — inject your knowledge"),
        P("<b>Reads:</b> topic. <b>Writes:</b> enriched_context. Runs hybrid "
          "retrieval against <i>knowledge_db</i> and MMR retrieval against "
          "<i>reasoning_db</i>. The output is one labelled string with sections "
          "for each store — the format prompt depends on those labels."),
        section("filter_node — drop noise"),
        P("<b>Reads:</b> raw_articles. <b>Writes:</b> raw_articles (smaller). "
          "Heuristic dedup + signal-word scoring runs first. If we have enough "
          "articles, an LLM gets a JSON-only prompt to keep the strongest indices. "
          "On JSON parse failure the heuristic stands."),
        section("rank_node — pick the lead"),
        P("<b>Reads:</b> raw_articles. <b>Writes:</b> ranked_articles. Scores each "
          "article on topic relevance, debate value, recency, source quality. News "
          "domains get a +6 boost, encyclopedia URLs get a −8 penalty. "
          "<i>_promote_news_first</i> guarantees the lead is a current-affairs piece."),
        section("summarize_node — one prompt per article"),
        P("<b>Reads:</b> ranked_articles, enriched_context. <b>Writes:</b> "
          "summaries, key_facts, concepts. Loops the top 5 articles, sends each "
          "through the same SUMMARY/KEY FACT/CONCEPT template, parses the response. "
          "Caches each prompt by article content so re-runs don't burn tokens."),
        callout("Bug we fixed — article contamination",
                "An earlier version batched all articles into one prompt. The LLM "
                "would attribute one article's stat to another article's title. "
                "Per-article looping fixed the alignment but cost more tokens — we "
                "balanced it by capping article content at 2500 chars and the "
                "loop at 5 articles.",
                kind="warn"),
        section("argue_node — for/against/middle"),
        P("<b>Reads:</b> topic, summaries, RAG context. <b>Writes:</b> arguments "
          "= {for, against, middle}. JSON-only prompt asking for exactly three "
          "items per side. <i>_normalize_arg_list</i> pads with heuristics if the "
          "LLM returns fewer than three."),
        section("coach_node — the debate packet"),
        P("<b>Reads:</b> topic, arguments, RAG style chunks. <b>Writes:</b> "
          "debate_angle, debate_packet. The packet has nine named fields: unique "
          "angle, value clash, burden of proof, mechanism, opening line, claim/"
          "warrant/impact, top rebuttal, judge language, power phrases. The "
          "format node depends on those labels."),
        section("english_coach_node — Word Power lesson"),
        P("<b>Reads:</b> topic, english_db retrieval. <b>Writes:</b> "
          "english_lesson, vocab_words, word_roots. Pulls etymology and definition "
          "chunks, asks for a JSON lesson, falls back to a curated word bank when "
          "retrieval is noisy."),
        section("format_node — assemble for delivery"),
        P("<b>Reads:</b> everything. <b>Writes:</b> final_doc. Pure heuristic — "
          "no LLM call. Lays out nine sections: TOPIC FOR TODAY, PRE-KNOWLEDGE, "
          "WORD BEFORE YOU READ, TODAY'S ARTICLE / CASE, YOUR DEBATING BUILD, "
          "REBUTTAL DRILLS, WEIGHING LANGUAGE TO USE, VOCAB SESSION, THINGS TO "
          "TAKE CARE. Trims each block to a Telegram-safe size."),
        callout("Drift to fix — Telegram splitter",
                "delivery/telegram.py knows seven section titles. format_node emits "
                "nine. REBUTTAL DRILLS and WEIGHING LANGUAGE TO USE currently get "
                "glued onto the previous message. Add them to SECTION_TITLES.",
                kind="warn"),
    ]


def chapter_memory() -> list:
    return [
        PageBreak(),
        *chapter(9, "Memory — what the system remembers between runs"),
        lead("Without memory, every morning is the system's first morning. "
             "We keep memory deliberately small."),
        P("Without memory, the night agent would have nothing to quiz you on and "
          "the weekend agent would have nothing to distill. "
          "<i>memory/weekly_store.py</i> is a thin layer over a single JSON file."),
        section("The schema, kept deliberately small"),
        P("Every daily run appends an entry keyed by today's date. The entry "
          "stores compact fields only — three bullet summaries, two key facts, "
          "three concepts, the debate angle as one string, vocab as three words. "
          "<b>We never store raw article bodies in memory.</b> Raw text would "
          "bloat the JSON to MBs and slow every read."),
        code("log['2026-06-05'] = [{\n"
             "  'topic': 'feminism',\n"
             "  'summaries': ['...', '...'],\n"
             "  'key_facts': ['...'],\n"
             "  'concepts': ['...'],\n"
             "  'debate_angle': '...',\n"
             "  'studied': False,\n"
             "  'quiz_score': None,\n"
             "  'timestamp': '2026-06-05T08:01:14+00:00',\n"
             "}]"),
        section("Atomic writes — no half-written files"),
        P(f"<i>save_log</i> writes to a temp file in the same directory and then "
          f"calls {term('os.replace', 'an OS-level rename that is atomic — either fully succeeds or fully fails, never half-applied')}. "
          "If the runner crashes mid-write, the original log is untouched. The "
          "temp file lives in the same dir so the rename stays atomic on every "
          "filesystem we care about."),
        buzz("Atomic operation",
             "An operation that either fully completes or has no effect at all — "
             "there's no half-done state observers can see. <i>os.replace</i> is "
             "atomic; a plain <i>write()</i> followed by another <i>write()</i> is not."),
        section("UTC timestamps"),
        P(f"Earlier versions used <i>datetime.now().isoformat()</i> — a "
          f"{term('naive', 'naive datetime = no timezone attached — interpreted as local time')} local timestamp. "
          "Dev runs landed in IST, GitHub Actions in UTC. We replaced every "
          "call with <i>datetime.now(timezone.utc).isoformat()</i>. Every entry "
          "now agrees on the wall clock."),
        buzz("UTC",
             "<i>Coordinated Universal Time</i> — the world's primary time "
             "standard, the same everywhere. Always store and compare timestamps "
             "in UTC; convert to local time only when displaying to a human."),
        callout("Lesson — store what compounds",
                "Memory is not a transcript. Memory is the distilled signal that "
                "next week's recap will build on. If a field doesn't help the "
                "weekend agent, it doesn't belong in the log."),
    ]


def chapter_night_weekend() -> list:
    return [
        PageBreak(),
        *chapter(10, "Night and weekend loops — the reinforcement layer"),
        lead("Without these two loops the system is just a newsletter. With "
             "them it's a learning tool."),
        P("Information delivered in the morning is forgotten by evening. The night "
          "agent and weekend agent exist to make today's lesson stick."),
        section("Night agent — three-way branch"),
        P("At 10:30 PM the scheduler sends you a check-in. Your reply determines "
          "the path:"),
        bullets([
            "<b>yes</b> → MCQ debate quiz built from today's memory.",
            "<b>english</b> → vocabulary quiz from the Word Power store.",
            "<b>no</b> or no reply → compressed 100-word bedtime recap.",
        ]),
        P("The debate quiz is a real five-question multiple-choice exam, scored "
          "by exact letter match (<i>1a 2b 3c 4d 5a</i>). The LLM builds the quiz "
          "from today_log; on token-bloat 413 errors the heuristic MCQ builder "
          "takes over."),
        section("Weekend agent — distill the week"),
        P("Sunday morning the scheduler reads the last seven days of memory and "
          "asks the reasoning model to filter ruthlessly: keep only concepts, "
          "frameworks, statistics, and argument patterns. Anything topical, "
          "anecdotal, or shelf-life-bound gets dropped."),
        section("Spaced repetition without the framework"),
        P(f"<i>agents/topic_selector.py</i> sorts priority topics by "
          "(seen_today_penalty, -days_since, appearances, index). Topics not "
          "studied for the longest time bubble to the top; topics already "
          f"studied today sink. Conceptually it's {term('spaced repetition', 'showing material at increasing intervals so you review it just as you are about to forget — the principle behind Anki, Quizlet, Duolingo')} — "
          "the implementation is twenty lines."),
        callout("Tip — reinforcement is the point",
                "Without the night and weekend loops this project is just a "
                "newsletter. With them it's a learning system. Treat them as "
                "first-class features, not nice-to-haves.",
                kind="tip"),
    ]


def chapter_delivery() -> list:
    return [
        PageBreak(),
        *chapter(11, "Delivery — how the lesson reaches your phone"),
        lead("Delivery looks trivial. We migrated providers three times before "
             "landing on something that actually worked end to end."),
        P("Every migration only touched <i>delivery/</i>. The pipeline never "
          "knew the channel had changed. That's the payoff of keeping I/O out of "
          "your business logic."),
        section("Phase one — Twilio WhatsApp sandbox"),
        P("Twilio is the textbook choice. We started there. Two problems killed "
          "it: trial accounts cap out fast, and the sandbox would silently "
          "downgrade WhatsApp messages to SMS when the channel prefix wasn't "
          "exactly right. The bug looked like the code; the cause was a config "
          "string."),
        section("Phase two — Meta WhatsApp Cloud API"),
        P(f"Better economics (1000 free conversations per month), but Meta's "
          f"reply detection requires a public {term('webhook', 'a URL on a publicly-reachable server that the provider calls when something happens — needs hosting and a stable IP')}. "
          "GitHub Actions runners don't have a public IP. We considered standing "
          "up a free-tier Flask server, then asked whether the complexity was worth it."),
        section("Phase three — Telegram bot"),
        P(f"Telegram has no conversation cap, no 24-hour session window, and a "
          f"{term('pull-based', 'your code asks for new messages on a schedule, instead of the provider pushing them at you')} reply API. "
          "The night agent calls <i>bot.get_updates()</i> every ten seconds until "
          "it sees your message. No webhook, no server, no template approval."),
        buzz("Webhook vs polling",
             "<b>Webhook</b> = provider calls you. Requires you to be reachable "
             "at a fixed URL. <b>Polling</b> = you call the provider on a "
             "schedule. Works from anywhere, even a stateless runner. Polling "
             "is slower (you check 10s after a message arrives, not the instant "
             "it does), but for our use case 10s is fine."),
        section("Section-by-section sending"),
        P("The full digest is too long for one Telegram message. <i>send_digest</i> "
          "splits the final document on the section headers (TOPIC FOR TODAY, "
          "PRE-KNOWLEDGE, etc.) and sends each block as its own chat message. "
          "Reading on a phone feels like nine bite-sized cards, not one wall."),
        callout("Lesson — delivery is an I/O contract",
                "Every migration only touched delivery/. The pipeline never knew "
                "the channel had changed. That's the payoff of keeping I/O out of "
                "your business logic."),
    ]


def chapter_automation(assets: dict) -> list:
    return [
        PageBreak(),
        *chapter(12, "Automation — GitHub Actions"),
        lead("Turn a script you run by hand into a service that runs itself "
             "three times a day, for free, with state that survives between runs."),
        P(f"A learning system that requires you to manually run a Python script "
          f"every morning is not a learning system. {term('GitHub Actions', 'free CI/CD platform built into every GitHub repo — runs scripts on push, on a schedule, or manually')} "
          f"runs main.py for you on a {term('cron', 'a way of expressing schedules with five numbers — minute, hour, day-of-month, month, day-of-week')} "
          "schedule and gives you a free-tier runner with cache and commit-back."),
        buzz("Runner",
             "The virtual machine GitHub spins up to execute your workflow. "
             "Stateless by default — every run starts fresh. We use the cache "
             "and a commit-back trick to give it memory."),
        section("Three schedules"),
        bullets([
            "<b>02:30 UTC weekdays</b> → 08:00 IST → daily digest.",
            "<b>17:00 UTC weekdays</b> → 22:30 IST → night agent.",
            "<b>03:30 UTC Sunday</b> → 09:00 IST → weekend distillation.",
        ]),
        Spacer(1, 2 * mm),
        *image_block(assets["actions_cycle"], width_mm=150,
                     caption="One scheduler run, end to end. Cache + commit-back make consecutive runs see each other."),
        section("How a single run flows"),
        P("Checkout the repo → install with uv → restore the FAISS cache → "
          "rebuild it if missing → determine which mode to run by inspecting the "
          "cron value → run main.py with secrets injected → after the run, commit "
          "weekly_log.json back to main so the next night/weekend run sees it."),
        section("Why we commit memory back"),
        P("GitHub Actions runners are stateless. Without commit-back, every "
          "morning's digest would land into a fresh empty log and the night quiz "
          "would have nothing to quiz on. Commit-back gives us free durable state "
          "with no extra infrastructure."),
        callout("Warning — keep this repo private",
                "Commit-back puts your topics, debate angles, and quiz scores into "
                "git history. If the repo is public, that is public too. main.py "
                "prints a one-time reminder at startup unless DEBATEIQ_SILENCE_PRIVACY=1.",
                kind="warn"),
        section("Caching the FAISS index"),
        P(f"Rebuilding the index from PDFs takes a few minutes and burns Gemini "
          f"embedding quota. The workflow restores the previous run's index from "
          f"{term('actions/cache', 'a GitHub Actions feature that saves a directory between runs, keyed by a hash you choose')} "
          "keyed by the hash of sources.json, the extractor, and the chunker. "
          "If you don't change those, the cache stays warm forever."),
        buzz("Cache key",
             "The string that identifies a stored cache entry. If the key "
             "changes, the cache misses and you rebuild from scratch. We hash "
             "the files that affect the index so a config change invalidates "
             "the cache automatically."),
        section("Secrets"),
        P("Anything sensitive lives in the repo's Settings → Secrets → Actions. "
          "The workflow names them with the same env-var names the Python code "
          "expects. Rotation is a one-place change."),
    ]


def chapter_testing() -> list:
    return [
        PageBreak(),
        *chapter(13, "Testing strategy"),
        lead("Five test files, no real API calls. Each stubs the network and "
             "the LLM so the suite runs in seconds with zero quota burn."),
        P("The codebase has five test files. None of them require network or "
          "API keys — they all stub the external surfaces."),
        buzz("Stub / mock / fake",
             "Loose synonyms for 'a fake version of an external dependency you "
             "use in tests'. We use plain Python objects that mimic the real "
             "API just enough for the pipeline to run."),
        section("Why no pytest framework"),
        P("Each file is a script that runs assertions and prints a single "
          "success line. CI runs them with <i>python tests/test_X.py</i>. We could "
          "convert them to pytest but the simpler setup is fine for a project of "
          "this size."),
        section("What each test covers"),
        bullets([
            "<b>test_router.py</b> — every task_type routes to the expected model key.",
            "<b>test_memory.py</b> — read/write of weekly_log.json round-trips cleanly.",
            "<b>test_weekend.py</b> — _compute_stats and _heuristic_weekend_knowledge produce the right shapes.",
            "<b>test_rag.py</b> — splitter map, embedding map, retrieval pipeline, source validation.",
            "<b>test_daily_e2e.py</b> — full daily graph with stubbed tools and a fake LLM, asserts every state field is populated.",
        ]),
        section("Stubbing pattern"),
        P(f"The e2e test {term('monkey-patches', 'temporarily overwrites a function or class attribute on an imported module — convenient for testing')} "
          "the tool functions and the LLM pool before importing the graph. The "
          "graph then walks the full pipeline using a deterministic fake LLM that "
          "recognises each prompt by a key phrase and returns a hardcoded response."),
        buzz("End-to-end (e2e) test",
             "Exercises the whole system from input to output, not just one "
             "function. Slower than unit tests, but catches integration bugs "
             "that unit tests miss."),
        callout("Tip — fake LLMs are gold",
                "A 50-line fake LLM lets you exercise the entire pipeline in a "
                "tenth of a second with zero quota. We add a new case to it "
                "whenever a new node lands.",
                kind="tip"),
    ]


def chapter_bugs(assets: dict) -> list:
    bugs = [
        ("Pre-flight ping doubled LLM calls",
         "Every fallback lookup called invoke('ping') first.",
         "Quota burned twice as fast; some failures still slipped through because the ping passed but the real call 429d.",
         "Replaced eager check with a lazy proxy that only tries each candidate on real invocation.",
         "Defensive checks that cost as much as the thing they protect are anti-defensive."),
        ("Topic dict treated as string",
         "_load_topics_config returned the raw priority_topics list of dicts.",
         "First node that ran topic.upper() crashed with AttributeError. Daily mode was unusable without --topic override.",
         "Loader now flattens to list[str]; nodes also normalise via topic_name() as belt-and-braces.",
         "If two parts of the system disagree on a shape, freeze the contract once and enforce it at the boundary."),
        ("Article contamination",
         "summarize_node batched articles into one LLM prompt.",
         "Summary[0] could quote article[2]'s fact. Format node then attributed the wrong title to the wrong content.",
         "One LLM call per article. Cap content at 2500 chars to keep total tokens under the per-minute limit.",
         "Batching is a perf optimisation that costs you correctness. Loop until you have a reason not to."),
        ("Reference pages winning rank",
         "Heuristic only scored topic-term frequency. Wikipedia hits scored very high.",
         "TODAY'S ARTICLE / CASE often opened with an encyclopedia summary instead of a live news piece.",
         "Added _is_news_article (+6) and _is_reference_article (-8); _promote_news_first re-orders after every rank path.",
         "Real-world quality lives in metadata, not in token frequency."),
        ("Night quiz 413 — too many tokens",
         "_generate_quiz_with_llm dumped the whole today_log into the prompt.",
         "20K+ tokens vs 6-12K TPM caps. Every LLM model rejected; heuristic fallback always ran.",
         "Trim today_log to topic+key_facts+concepts before serialising. Skip raw debate_angle and english_lesson.",
         "Free-tier limits are not optional. Audit prompt size before merging any node that touches memory."),
        ("FAISS segfaults on Windows",
         "chromadb 1.5.9 native layer crashed under our query load.",
         "Whole scheduler run died mid-ingest with exit code 139.",
         "Migrated to FAISS — leaner persistence, no native crashes on the boxes we run on.",
         "Pick the simpler persistence layer unless you need the heavier DB semantics."),
        ("Twilio WhatsApp downgraded to SMS",
         "Channel prefix on the To: field wasn't propagating in the sandbox.",
         "Daily digests arrived as expensive SMS; replies couldn't be polled back.",
         "Replaced Twilio with Telegram. Cheaper, simpler, pull-based replies.",
         "When a provider's failure modes outnumber its features, switch providers."),
        ("Broken proxy env vars",
         "HTTP_PROXY=http://127.0.0.1:9 lingered in the shell from an earlier experiment.",
         "Every outbound network call from Tavily/Wiki/RSS/DDG silently returned empty.",
         "Added clear_broken_local_proxies() to startup of every network-touching module.",
         "Transport errors masquerade as application bugs. Always scrub the environment first."),
        ("BM25 corpus empty",
         "build_hybrid_retriever called BM25Retriever.from_texts([]).",
         "Every 'hybrid' retriever silently degraded to pure vector. The 40/60 mix was a lie.",
         "Pull the texts from the FAISS docstore (or Chroma.get) and feed BM25 with them.",
         "A test that asserts a non-empty retrieval result would have caught this in minutes."),
        ("Reply timeout hung the night agent",
         "wait_for_reply with no env vars looped forever.",
         "Local runs without WhatsApp credentials never returned.",
         "Treat missing credentials as 'no reply' and degrade to bedtime mode.",
         "Every blocking call needs a documented exit on a missing precondition."),
        ("Gemini model decommissioned",
         "gemini-1.5-pro and 1.5-flash were retired without notice in our usage path.",
         "Coach lane 404'd on every run.",
         "Centralised model strings in llm_pool.py; updated to gemini-2.5-pro / 2.5-flash, later moved 'best' to Groq gpt-oss-120b.",
         "Provider deprecation is a fact of life. Keep model strings in one place and read the deprecation notices."),
        ("LangChain 0.3 dropped pydantic_v1",
         "langchain-groq 0.1.x imported from langchain_core.pydantic_v1.",
         "Whole project failed to import after bumping langchain-core.",
         "Bumped langchain-groq, langchain-google-genai, switched EnsembleRetriever import to langchain_classic.",
         "Pin the whole langchain family together. Upgrading one without the rest is a guaranteed afternoon lost."),
        ("Format vs Telegram section drift",
         "format_node emits nine sections; delivery/telegram.py knows seven.",
         "REBUTTAL DRILLS and WEIGHING LANGUAGE TO USE merge into the previous message instead of standing alone.",
         "Add the missing labels to SECTION_TITLES. Better: derive the title list from format_node.",
         "Two places that must agree on a list will diverge. Make the list live in one of them."),
        ("Naive timestamps in memory",
         "datetime.now().isoformat() returned local TZ.",
         "Dev (IST) and CI (UTC) entries mixed in the same log; weekend windowing was off by hours on Sundays.",
         "Centralised on _now_iso() = datetime.now(timezone.utc).isoformat().",
         "Time math without timezones is a quiet bug factory."),
    ]

    items = [
        PageBreak(),
        *chapter(14, "Bug archaeology — what broke and why"),
        lead("Every bug we fixed is a small lesson that pays compounding "
             "interest. Read this chapter slowly."),
        P("The shape of each entry is the same: <b>symptom</b> (what you saw), "
          "<b>root cause</b> (what was actually wrong), <b>fix</b> (the smallest "
          "correct change), <b>lesson</b> (what you'll keep doing forever)."),
        Spacer(1, 4 * mm),
        *image_block(assets["bug_anatomy"], width_mm=140,
                     caption="The four-question template we apply to every bug."),
    ]
    for i, (title, symptom, root, fix, lesson) in enumerate(bugs, start=1):
        items.append(P(f"Bug {i}: {title}", "SectionTitle"))
        items.append(P(f"<b>Symptom.</b> {symptom}"))
        items.append(P(f"<b>Root cause.</b> {root}"))
        items.append(P(f"<b>Fix.</b> {fix}"))
        items.append(callout("Lesson", lesson, kind="info"))
    return items


def chapter_extending() -> list:
    return [
        PageBreak(),
        *chapter(15, "Extending the project"),
        lead("Five common changes you'll want to make and the smallest path "
             "to each."),
        section("Add a new topic"),
        bullets([
            "Open <i>topics.json</i>.",
            "Add an entry under <i>priority_topics</i> with topic, debate_frames, keywords, frameworks, live_cases.",
            "Optionally upload a related PDF into <i>knowledge_base/pdfs/topic_pdfs/</i> and add it to <i>rag/sources.json</i>.",
            "Re-ingest only the new lane: <i>python rag/ingest.py --only topic_pdf</i>.",
        ]),
        section("Add a new research tool"),
        bullets([
            "Create <i>tools/your_tool.py</i> with a single function <i>your_tool_search(query) -&gt; list[dict]</i>.",
            "Return dicts with the canonical keys: title, url, content, source, published.",
            "Import and call it in <i>agents/research_node.py</i> inside the ThreadPoolExecutor.",
            "Add a test in <i>tests/test_tools.py</i> that asserts your tool returns the right shape on a known query.",
        ]),
        section("Add a new pipeline node"),
        bullets([
            "Decide what it reads and writes. Add the new fields to <i>core/state.py</i>.",
            "Create <i>agents/my_node.py</i> with a function <i>my_node(state) -&gt; state</i>.",
            "Always provide a heuristic fallback so the node can never crash the graph.",
            "Wire it into <i>graph.py</i> with <i>add_node</i> + <i>add_edge</i>.",
            "Add a fake-LLM case to <i>tests/test_daily_e2e.py</i>.",
        ]),
        section("Swap an LLM provider"),
        bullets([
            "Edit only <i>core/llm_pool.py</i>.",
            "Keep the role keys (fast/balanced/structured/reasoning/long_ctx/best); change the model strings.",
            "Add fallback for the new model in <i>core/fallback.py</i> if it lives in a different chain.",
            "Run the smokes — they'll surface any prompt-shape incompatibility immediately.",
        ]),
        section("Change the digest layout"),
        bullets([
            "Edit <i>agents/format_node.py</i>.",
            "If you add or rename a section header, update <i>delivery/telegram.SECTION_TITLES</i> in the same commit.",
            "Run <i>test_daily_e2e</i> — it asserts the final doc still contains the expected header.",
        ]),
    ]


def chapter_debugging() -> list:
    return [
        PageBreak(),
        *chapter(16, "Debugging playbook"),
        lead("When something breaks, this is the first chapter you open."),
        P("Symptoms you'll see in the wild, mapped to the first three places to "
          "look. If none of those resolve it, the bug is worth its own archaeology "
          "entry."),
        section("'I'm not getting the Telegram message'"),
        bullets([
            "Is the GitHub Actions run green? If not, read the last step's logs.",
            "Are TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID set as repo secrets?",
            "Did you start a chat with your own bot? Telegram won't deliver to a chat that hasn't opened.",
        ]),
        section("'The digest is empty / fallbacks only'"),
        bullets([
            "Quota: check Groq and Gemini consoles for the day's usage.",
            "Network: from a local shell run python -c 'import requests; print(requests.get(\"https://api.groq.com\").status_code)'.",
            "Proxy: confirm no HTTP_PROXY env var lurking in the runner.",
        ]),
        section("'RAG returns nothing'"),
        bullets([
            "Does <i>faiss/</i> exist on the runner? Cache key may have invalidated.",
            "Was the index built with the current embedding model? Old embeddings can't be queried with new ones.",
            "Try <i>python rag/ingest.py --only knowledge_db</i> and watch for [Sources] warnings.",
        ]),
        section("'Night quiz LLM call fails every time'"),
        bullets([
            "Print the prompt length. If it's &gt; 12K tokens you're hitting TPM caps.",
            "Trim <i>today_log</i> before serialising — drop debate_angle and english_lesson.",
            "Confirm the heuristic fallback is firing; if not, the exception isn't being caught.",
        ]),
        section("'GitHub Actions cron isn't firing'"),
        bullets([
            "GitHub disables scheduled workflows on repos with no recent commits. Push anything (even a comment) to wake it.",
            "Cron is UTC. Compute the local time from the cron expression before debugging.",
            "<i>workflow_dispatch</i> always works. Use it to verify the workflow itself is healthy.",
        ]),
    ]


def chapter_glossary() -> list:
    glossary = [
        ("Agent", "A function that takes the shared state, does work, and returns the state. The 'AI' part of 'agentic AI' is just smart functions composed in a graph."),
        ("BM25", "A keyword-search ranking function from the IR world. Older than embeddings; still wins on exact-term recall. We combine it with vectors in hybrid retrieval."),
        ("Callback / commit-back", "Pattern where the scheduled job commits its state back to git so the next run can read it. Free durable storage for personal projects."),
        ("Chunk", "A piece of a source document small enough to embed cleanly. The size and overlap matter more than people realise."),
        ("Cron", "Unix time expression. <i>30 2 * * 1-5</i> means '02:30 UTC, Monday to Friday'. GitHub Actions uses the same syntax."),
        ("Embedding", "A high-dimensional vector representing the meaning of a piece of text. Similar meanings → similar vectors → close in space."),
        ("EnsembleRetriever", "LangChain class that runs multiple retrievers and weights their results. We use it to mix BM25 (40%) and vector (60%) on knowledge_db."),
        ("FAISS", "Facebook's vector index library. Fast, persistent, lean. Default backend now that we left Chroma."),
        ("Fallback chain", "Ordered list of model keys to try when the primary fails. Defined in <i>core/fallback.py FALLBACK_CHAINS</i>."),
        ("Flowable", "A ReportLab term for an element that flows down the page — a paragraph, an image, a table. The PDF generator stitches flowables together."),
        ("Heuristic", "The non-LLM fallback path in every node. Less elegant than the LLM output but always available."),
        ("Hybrid retrieval", "BM25 + vector retrieval combined with weights. Better than either alone on factual material."),
        ("LangGraph", "The orchestrator. We declare nodes and edges; it runs them in the right order."),
        ("MMR", "Maximum Marginal Relevance. A retrieval strategy that penalises redundancy so the chunks you get back cover different angles."),
        ("Node", "One function in the LangGraph pipeline. In our project each node lives in its own file under <i>agents/</i>."),
        ("Prompt cache", "Disk file storing past LLM responses keyed by (scope, model, prompt) hash. Saves tokens on repeat runs."),
        ("RAG", "Retrieval-Augmented Generation. Pull your own material into the LLM prompt instead of relying on what the model already knows."),
        ("Router", "The function that maps task_type to a model key. Keeps the choice of model out of every node."),
        ("Spaced repetition", "Show a topic again only after enough time has passed that you've nearly forgotten it. Our topic selector does a lightweight version."),
        ("State", "The single mutable dict that every node reads from and writes to. Shape is defined in <i>core/state.py</i>."),
        ("TypedDict", "A Python type that lets you declare a dict's expected keys and value types. The editor checks them."),
        ("UTC", "Universal Coordinated Time. All timestamps in <i>memory/weekly_log.json</i> are in UTC because the runner and your laptop are in different time zones."),
        ("uv", "A fast Python package manager. Drop-in replacement for pip with better dependency resolution and parallel downloads."),
    ]
    items = [
        PageBreak(),
        *chapter(17, "Glossary"),
        P("Words that appear throughout this book, defined once and for all."),
        Spacer(1, 3 * mm),
    ]
    for term, defn in glossary:
        items.append(P(f"<b>{term}.</b> {defn}", "Body"))
    return items


def chapter_closing() -> list:
    return [
        PageBreak(),
        *chapter(18, "Where to go from here"),
        section("Read in this order"),
        bullets([
            "main.py — the entry point.",
            "graph.py — the wiring.",
            "core/state.py — the contract.",
            "topics.json — the curriculum.",
            "agents/research_node.py — the first real node.",
            "rag/retrieval_pipeline.py — the heart of RAG.",
            "agents/coach_node.py — the heart of the lesson.",
            "agents/format_node.py — how a state dict becomes a digest.",
            "delivery/telegram.py — how a digest becomes a phone notification.",
            "memory/weekly_store.py — how today becomes history.",
            ".github/workflows/scheduler.yml — how all of this happens without you.",
        ]),
        section("If you change one thing this week"),
        P("Fix the format/Telegram section drift (chapter 8, last callout). It's "
          "the smallest change with the most visible impact: REBUTTAL DRILLS and "
          "WEIGHING LANGUAGE TO USE will finally arrive as their own Telegram "
          "messages instead of gluing onto the section before them."),
        section("If you change one thing this month"),
        P("Trim the today_log payload before sending it to the night quiz LLM. "
          "That single edit moves the night quiz from 'falls back to heuristic "
          "every time' to 'uses the real LLM most nights' — without spending a "
          "rupee more."),
        section("If you change one thing this quarter"),
        P("Build a webhook server on Render's free tier so Telegram replies "
          "arrive in real time instead of needing the scheduled job to be running. "
          "Then the night quiz can be triggered by your reply, not by the clock."),
        Spacer(1, 10 * mm),
        callout("Final note",
                "Every line of code in this project can be read, understood, and "
                "rewritten in a single afternoon. The architecture is small on "
                "purpose. If something feels too complex to change, the right "
                "move is almost always to delete it and rebuild it simpler — "
                "not to add an abstraction on top of it.",
                kind="info"),
    ]


# ---------------------------------------------------------------- build
def build():
    print("[handbook] rendering diagrams...")
    assets = render_all(ASSETS)

    print("[handbook] composing document...")
    doc = BaseDocTemplate(
        str(OUT),
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=LEFT, rightMargin=RIGHT,
        topMargin=TOP, bottomMargin=BOTTOM,
        title="DebateIQ Learning Handbook",
        author="DebateIQ",
    )

    cover_frame = Frame(LEFT, BOTTOM, PAGE_W - LEFT - RIGHT, PAGE_H - TOP - BOTTOM, id="cover")
    body_frame = Frame(LEFT, BOTTOM, PAGE_W - LEFT - RIGHT, PAGE_H - TOP - BOTTOM, id="body")

    doc.addPageTemplates([
        PageTemplate(id="cover", frames=cover_frame, onPage=_draw_cover_background),
        PageTemplate(id="body", frames=body_frame, onPage=_draw_background),
    ])

    story: list = []
    story += cover()
    story.append(NextPageTemplate("body"))
    story.append(PageBreak())
    story += how_to_read()
    story += chapter_big_picture(assets)
    story += chapter_folder_structure()
    story += chapter_prereqs()
    story += chapter_agent_state(assets)
    story += chapter_llm_layer(assets)
    story += chapter_research_tools()
    story += chapter_rag(assets)
    story += chapter_pipeline(assets)
    story += chapter_memory()
    story += chapter_night_weekend()
    story += chapter_delivery()
    story += chapter_automation(assets)
    story += chapter_testing()
    story += chapter_bugs(assets)
    story += chapter_extending()
    story += chapter_debugging()
    story += chapter_glossary()
    story += chapter_closing()

    doc.build(story)
    print(f"[handbook] wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
