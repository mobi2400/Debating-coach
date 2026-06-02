# DebateIQ Agent — Phase 1 Sprint Breakdown

> 10 focused sub-parts. Each sprint has a clear goal, exact files to build, what to test before moving on, and what the next sprint depends on. Do not move to the next sprint until the current one passes its checkpoint.

---

## Sprint 0 — Project Setup & Environment
**Goal:** Clean repo, all API keys working, base dependencies installed.

### Tasks
- Create the full folder structure exactly as defined in README
- Create `requirements.txt` with all dependencies
- Create `.env` with all 7 environment variables (empty values)
- Create `.gitignore` — must ignore `/chroma`, `.env`, `memory/weekly_log.json`
- Create `topics.json` with your 5 starting topics
- Test every API key individually with a single hello-world call
  - Groq → one `llm.invoke("hello")` call
  - Google Gemini → one `llm.invoke("hello")` call
  - Tavily → one search for "feminism"
  - Twilio → send one test WhatsApp message to yourself

### Files Created
```
debate-agent/
├── topics.json
├── requirements.txt
├── .env
├── .gitignore
└── (all empty folders with .gitkeep)
```

### Checkpoint ✅
- All folders exist
- All 4 API tests return a response without error
- WhatsApp test message received on your phone
- Git repo initialised and first commit pushed

### Dependencies for Next Sprint
None — this is the foundation everything else sits on.

---

## Sprint 1 — LLM Pool, Router & Fallback
**Goal:** All 6 LLMs defined, routing logic working, fallback chain tested.

### Tasks
- Build `core/llm_pool.py` — define all 6 LLMs with correct model strings and free-tier config
- Build `core/llm_router.py` — `route_by_task()` function mapping task_type strings to LLM keys
- Build `core/fallback.py` — fallback chain dict for every route, `get_llm_with_fallback()` function
- Build `core/state.py` — `AgentState` TypedDict with all fields from README
- Write a test script `tests/test_router.py` that calls every route and prints which LLM was selected
- Simulate a rate limit error on one LLM and confirm fallback kicks in

### Files Created
```
core/
├── llm_pool.py
├── llm_router.py
├── fallback.py
└── state.py
tests/
└── test_router.py
```

### Routing Map to Implement
| task_type | LLM |
|---|---|
| fetch | long_ctx (Gemini Flash) |
| filter | fast (Llama 8B) |
| rank | fast (Llama 8B) |
| summarize | balanced (Llama 70B) |
| argue | reasoning (DeepSeek R1) |
| debate | best (Gemini Pro) |
| format | structured (Mixtral) |
| quiz | structured (Mixtral) |
| bedtime | balanced (Llama 70B) |
| weekend | reasoning (DeepSeek R1) |

### Checkpoint ✅
- `test_router.py` correctly prints the right LLM for every task_type
- Fallback test passes — wrong model → correct fallback selected
- `AgentState` imports cleanly with no errors
- No hardcoded model strings outside `llm_pool.py`

### Dependencies for Next Sprint
Sprint 2 (research tools) and Sprint 3 (RAG) can both start after this. They are independent of each other.

---

## Sprint 2 — Research Tools
**Goal:** All 4 research tools working and returning clean structured output.

### Tasks
- Build `tools/tavily_tool.py`
  - `search_depth="advanced"`, `include_raw_content=True`, `max_results=5`
  - Output: list of dicts with `title`, `url`, `content`, `source`
- Build `tools/wiki_tool.py`
  - `top_k_results=2`, `doc_content_chars_max=3000`
  - Output: dict with `summary` and `content`
- Build `tools/rss_tool.py`
  - Configure feeds: BBC, Al Jazeera, Reuters, The Hindu, Indian Express
  - Parse with `feedparser`, return last 24 hours only
  - Output: list of dicts with `title`, `link`, `summary`, `published`
- Build `tools/ddg_tool.py`
  - Wrapper around `DuckDuckGoSearchRun`
  - Output: same structure as Tavily for consistency
- Build `tests/test_tools.py`
  - Run each tool against the query "feminism India"
  - Print output count and first result for each

### Files Created
```
tools/
├── tavily_tool.py
├── wiki_tool.py
├── rss_tool.py
└── ddg_tool.py
tests/
└── test_tools.py
```

### Checkpoint ✅
- Each tool returns at least 1 result for "feminism India"
- All outputs follow the same dict structure (consistent keys)
- RSS only returns articles from the last 24 hours
- No tool crashes when a source is unavailable — it returns empty list, not an error
- Total tool call for one topic takes under 30 seconds

### Dependencies for Next Sprint
Sprint 4 (Research Agent node) depends on this being done.

---

## Sprint 3 — RAG Pipeline (Ingest + Retrieval)
**Goal:** All 3 ChromaDB vector stores built, all 3 retrievers working and returning relevant chunks.

### Tasks

**Part A — Chunking**
- Build `rag/chunking_strategy.py` with all 4 splitters
  - `knowledge_splitter`: RecursiveCharacterTextSplitter, chunk=600, overlap=100
  - `style_splitter`: RecursiveCharacterTextSplitter, chunk=400, overlap=80
  - `reasoning_splitter`: SentenceTransformersTokenTextSplitter, tokens=180, overlap=30
  - `youtube_splitter`: RecursiveCharacterTextSplitter, chunk=300, overlap=60

**Part B — Embeddings**
- Build `rag/embeddings.py` with 3 models
  - `quality_embeddings`: all-mpnet-base-v2 → for knowledge_db
  - `fast_embeddings`: all-MiniLM-L6-v2 → for style_db
  - `qa_embeddings`: multi-qa-mpnet-base-dot-v1 → for reasoning_db

**Part C — Ingest**
- Build `rag/ingest.py`
  - `ingest_pdf(path, doc_type)` — PyMuPDF reader + correct splitter by doc_type
  - `ingest_youtube(video_id, channel_type)` — youtube-transcript-api + youtube_splitter
  - `ingest_website(url, site_type)` — BeautifulSoup + correct splitter by site_type
  - `build_knowledge_base(all_docs)` — routes each doc to correct ChromaDB store
- Add at least 2 real PDFs, 1 YouTube video, 1 website to `rag/sources.json`
- Run `ingest.py` end-to-end and confirm all 3 chroma folders are created

**Part D — Retrieval**
- Build `rag/retrieval_pipeline.py`
  - `build_hybrid_retriever()` — EnsembleRetriever with BM25 (40%) + Vector (60%)
  - `style_retriever` — similarity, score_threshold=0.72, k=4
  - `reasoning_retriever` — mmr, k=5, fetch_k=25, lambda_mult=0.65
  - `retrieve_for_node(node_name, query)` — applies correct ratios per node from README
  - `format_retrieved_context(chunks)` — formats into labelled sections

### Files Created
```
rag/
├── chunking_strategy.py
├── embeddings.py
├── ingest.py
├── retrieval_pipeline.py
└── sources.json
chroma/
├── knowledge_db/     ← auto-generated
├── style_db/         ← auto-generated
└── reasoning_db/     ← auto-generated
```

### Checkpoint ✅
- `ingest.py` runs without error
- All 3 chroma folders exist and are non-empty
- `retrieve_for_node("coach_node", "feminism argument")` returns chunks from style_db
- `retrieve_for_node("argue_node", "feminism")` returns chunks from reasoning_db with diversity
- `retrieve_for_node("rag_enrich_node", "feminism history")` returns chunks from knowledge_db
- Retrieved chunks are readable and on-topic (manual check)

### Dependencies for Next Sprint
Sprint 4 and Sprint 5 both depend on this.

---

## Sprint 4 — Daily Pipeline: Research → Rank
**Goal:** First half of the daily LangGraph pipeline working end-to-end on one topic.

### Tasks
- Build `agents/research_node.py`
  - Accepts `state["topic"]`
  - Calls all 4 tools in parallel using `asyncio.gather` or sequential calls
  - Combines results into `state["raw_articles"]` (list of dicts, consistent format)
  - Sets `state["task_type"] = "fetch"` before calling LLM if needed
- Build `agents/rag_enrich_node.py`
  - Calls `retrieve_for_node("rag_enrich_node", topic)`
  - Stores result in `state["enriched_context"]`
- Build `agents/filter_node.py`
  - Uses `get_llm_with_fallback(state)` with task_type="filter"
  - Prompt: given raw_articles list, remove duplicates and low-quality sources
  - Output: cleaned list back into `state["raw_articles"]`
- Build `agents/rank_node.py`
  - Uses Llama 8B
  - Scores each article 1–10 on relevance + recency
  - Picks top 5–7 into `state["ranked_articles"]`
- Build `graph.py` — partial graph with just these 4 nodes connected
- Build `main.py` — minimal version that runs one topic through these 4 nodes

### Files Created
```
agents/
├── research_node.py
├── rag_enrich_node.py
├── filter_node.py
└── rank_node.py
graph.py       ← partial
main.py        ← partial
```

### Checkpoint ✅
- Run `python main.py --mode daily --topic "feminism"` 
- `raw_articles` contains results from all 4 tools
- `enriched_context` contains relevant RAG chunks
- `ranked_articles` contains 5–7 articles, no duplicates
- All LLM calls go through the router — no hardcoded model calls in agent files
- State is clean and printable at each node for debugging

### Dependencies for Next Sprint
Sprint 5 continues the daily pipeline from where this ends.

---

## Sprint 5 — Daily Pipeline: Summarize → WhatsApp
**Goal:** Complete the daily pipeline through to a formatted WhatsApp message being sent.

### Tasks
- Build `agents/summarize_node.py`
  - Uses Llama 3.3 70B
  - For each article in `ranked_articles`, generates 3–4 bullet points in layman language
  - Also tags `key_facts` (list of strings) and `concepts` (list of strings) into state
  - Stores in `state["summaries"]`
- Build `agents/argue_node.py`
  - Uses DeepSeek R1
  - Calls `retrieve_for_node("argue_node", topic)` for RAG context
  - Generates 3 FOR, 3 AGAINST, 1 middle-ground
  - Stores in `state["arguments"]` as a dict with keys `for`, `against`, `middle`
- Build `agents/coach_node.py`
  - Uses Gemini 1.5 Pro
  - Calls `retrieve_for_node("coach_node", topic)` — style_db at 50%
  - Generates: unique angle, opening line, Claim-Warrant-Impact flow, top 3 rebuttals, 5 power phrases
  - Stores in `state["debate_angle"]`
- Build `agents/format_node.py`
  - Uses Mixtral
  - Compiles all state fields into one WhatsApp message string
  - No markdown, use emojis as section dividers
  - Splits into multiple messages if over 4096 characters
  - Stores in `state["final_doc"]`
- Build `delivery/whatsapp.py`
  - `send_message(text)` — sends via Twilio sandbox
  - `send_digest(final_doc)` — handles multi-message splitting
- Complete `graph.py` — full 8-node daily pipeline
- Complete `main.py` — full daily mode

### Files Created
```
agents/
├── summarize_node.py
├── argue_node.py
├── coach_node.py
└── format_node.py
delivery/
└── whatsapp.py
graph.py       ← complete daily pipeline
main.py        ← daily mode complete
```

### Checkpoint ✅
- Run `python main.py --mode daily`
- Full digest received on WhatsApp within 3–5 minutes
- Message has all sections: background, news, insights, arguments, coach section
- Coach section feels personalised based on your RAG content
- No markdown symbols visible in WhatsApp
- All 5 topics in `topics.json` processed (may take 15–20 min total)

### Dependencies for Next Sprint
Sprint 6 (memory) must come before Sprint 7 (Night Agent) because the quiz reads from memory.

---

## Sprint 6 — Memory System
**Goal:** Daily digest content saved to memory log. Read/write functions tested.

### Tasks
- Build `memory/weekly_store.py` with these functions:
  - `save_daily_digest(topic, content_dict)` — appends to today's entry in JSON
  - `mark_as_studied(date_str, studied, score=None)` — updates studied flag and quiz score
  - `get_week_log()` — returns last 7 days of entries
  - `get_today_log()` — returns today's entries only
  - `load_log()` and `save_log(log)` — internal read/write helpers
- Update `agents/summarize_node.py` — after summarizing, call `save_daily_digest()`
- Update `agents/format_node.py` — after formatting, confirm save happened
- Create `memory/weekly_log.json` with empty dict as starting state
- Write `tests/test_memory.py`
  - Simulate saving 3 days of entries
  - Read back with `get_week_log()` and confirm all data is there
  - Simulate marking one day as studied with score 80
  - Confirm the flag and score are persisted correctly

### Files Created
```
memory/
├── weekly_store.py
└── weekly_log.json
tests/
└── test_memory.py
```

### Memory Log Structure Per Entry
```json
{
  "2024-01-15": [
    {
      "topic": "feminism",
      "summary": "...",
      "arguments": { "for": [], "against": [], "middle": "" },
      "key_facts": [],
      "concepts": [],
      "debate_angle": "...",
      "studied": false,
      "quiz_score": null,
      "timestamp": "2024-01-15T08:32:00"
    }
  ]
}
```

### Checkpoint ✅
- `test_memory.py` passes all assertions
- After running full daily pipeline, `weekly_log.json` has today's entry with all fields populated
- `get_week_log()` returns correct data for the last 7 days
- `mark_as_studied()` correctly updates the right entry without overwriting others
- JSON file is human-readable (formatted with indent=2)

### Dependencies for Next Sprint
Sprint 7 (Night Agent) depends on this being done.

---

## Sprint 7 — Night Agent (Quiz + Bedtime)
**Goal:** Nightly check-in working. Both quiz mode and bedtime mode delivering correctly to WhatsApp.

### Tasks
- Build reply listener in `delivery/whatsapp.py`
  - `wait_for_reply(timeout_minutes)` — polls Twilio API for incoming messages
  - Returns the message body string or `"timeout"` if no reply
- Build `agents/night_agent.py`
  - Sends check-in message at invocation
  - Calls `wait_for_reply(30)`
  - Detects "yes" / "no" in reply (case-insensitive, handles typos like "yep", "nope", "y", "n")
  - Routes to `quiz_mode(state)` or `bedtime_mode(state)`
- Build quiz mode inside `night_agent.py`
  - Loads today's digest from `get_today_log()`
  - Uses Mixtral to generate 5 questions (2 factual, 2 argument, 1 application) as structured JSON
  - Sends questions to WhatsApp
  - Waits for answer reply (timeout 10 min)
  - Scores answers, calculates percentage
  - Sends results with correct answers and one-line explanations
  - Calls `mark_as_studied(today, True, score)`
- Build bedtime mode inside `night_agent.py`
  - Loads today's digest from `get_today_log()`
  - Uses Llama 70B to compress to max 100 words
  - Must contain: 1 key fact, 1 FOR argument, 1 AGAINST argument, 1 power phrase
  - Sends as casual friendly WhatsApp message
  - Calls `mark_as_studied(today, False)`
- Add `--mode night` to `main.py`

### Files Created / Updated
```
agents/
└── night_agent.py
delivery/
└── whatsapp.py     ← updated with reply listener
main.py             ← updated with night mode
```

### Checkpoint ✅
- Run `python main.py --mode night`
- Check-in message received on WhatsApp
- Reply "yes" → 5 questions received, answer them, score received with explanations
- Reply "no" → bedtime summary received, under 100 words, readable in 2 minutes
- `weekly_log.json` updated correctly after both paths
- Timeout works — if no reply in 30 min, no crash

### Dependencies for Next Sprint
Sprint 8 (Weekend Agent) depends on Sprint 6 memory being complete and at least a few days of log entries.

---

## Sprint 8 — Weekend Agent
**Goal:** Weekend Agent reads full week log, filters ruthlessly, sends Weekly Brain Upload.

### Tasks
- Build `agents/weekend_agent.py`
  - `weekend_agent_node(state)` — main entry function
  - Calls `get_week_log()` from memory store
  - Builds filtering prompt with strict rules (see README — what gets filtered out vs kept)
  - Uses DeepSeek R1 to filter and structure into JSON with 4 categories:
    - `concepts` — title, what_it_is, why_it_matters_in_debate, remember_this, source_topic
    - `frameworks` — same structure
    - `key_stats` — stat, context, use_in_debate
    - `argument_patterns` — pattern_name, how_it_works, example
  - Parses the JSON response safely with try/except
  - Calculates weekly stats: days_studied out of 5, average quiz score
  - Formats into Weekly Brain Upload WhatsApp message
  - Sends via `delivery/whatsapp.py`
- Add `--mode weekend` to `main.py`
- Write `tests/test_weekend.py`
  - Feed it mock week data with a mix of news and concepts
  - Confirm the filter removes news and keeps concepts
  - Confirm output JSON parses correctly

### Files Created / Updated
```
agents/
└── weekend_agent.py
tests/
└── test_weekend.py
main.py             ← updated with weekend mode
```

### Checkpoint ✅
- Run `python main.py --mode weekend` with at least 3 days of real memory log data
- Brain Upload received on WhatsApp
- Output contains only concepts, frameworks, stats, patterns — no news stories
- Weekly stats (days studied, avg score) are accurate
- JSON parsing does not crash on edge cases (empty week, no quiz scores)
- Message is readable and well-structured

### Dependencies for Next Sprint
Sprint 9 (Scheduler) depends on all 3 modes being independently working.

---

## Sprint 9 — Scheduler, Final Integration & Testing
**Goal:** All 3 pipelines running automatically on schedule. Full end-to-end tested. System is production-ready.

### Tasks

**Part A — GitHub Actions**
- Build `.github/workflows/scheduler.yml`
  - 3 cron triggers with correct UTC times for IST
  - Daily: `30 2 * * 1-5` (8:00 AM IST)
  - Nightly: `0 17 * * 1-5` (10:30 PM IST)
  - Weekend: `30 3 * * 0` (9:00 AM IST Sunday)
  - Each trigger runs `python main.py --mode [daily/night/weekend]`
  - All secrets set in GitHub repo Settings → Secrets
  - Checkout, Python setup, pip install steps included

**Part B — main.py Final Version**
- Clean argument parsing with `argparse`
- `--mode daily` → runs daily pipeline graph
- `--mode night` → runs night agent
- `--mode weekend` → runs weekend agent
- `--topic` optional override for testing single topic
- Proper logging to stdout for GitHub Actions log visibility

**Part C — End-to-End Test**
- Manually trigger each GitHub Actions workflow from the Actions tab
- Confirm daily digest arrives on WhatsApp
- Confirm night check-in arrives and both paths work
- Confirm weekend brain upload arrives
- Check GitHub Actions logs for any hidden errors

**Part D — Hardening**
- Every external API call wrapped in try/except with informative error message
- Every LLM call uses `get_llm_with_fallback()` — no direct LLM calls
- RSS tool returns empty list gracefully if a feed is down
- WhatsApp sender retries once on failure before giving up
- `weekly_log.json` never corrupted — always load → modify → save, never overwrite directly

### Files Created / Updated
```
.github/workflows/
└── scheduler.yml
main.py             ← final complete version
```

### Checkpoint ✅
- All 3 GitHub Actions workflows trigger successfully from the Actions tab
- All 3 WhatsApp messages received correctly
- No unhandled exceptions in any GitHub Actions log
- Simulate Tavily being down → system falls back to DuckDuckGo without crashing
- Simulate Groq rate limit → fallback LLM used automatically
- Run full week simulation (5 daily runs + 1 weekend) → memory log correct, brain upload accurate
- `README.md` updated with any setup steps discovered during integration

### Final Project Checkpoint ✅
- Daily digest arrives every morning without manual trigger
- Nightly check-in works both paths
- Weekly brain upload runs Sunday morning
- Zero crashes across a full week of automated runs
- All API keys on free tier — no unexpected charges

---

## Sprint Summary

| Sprint | Focus | Key Output |
|---|---|---|
| 0 | Setup & environment | Repo, keys, folder structure |
| 1 | LLM pool, router, fallback | All 6 LLMs routable with fallback |
| 2 | Research tools | 4 tools returning clean structured data |
| 3 | RAG pipeline | 3 vector stores built, all retrievers working |
| 4 | Daily pipeline pt.1 | Research → RAG Enrich → Filter → Rank |
| 5 | Daily pipeline pt.2 | Summarize → Argue → Coach → Format → WhatsApp |
| 6 | Memory system | weekly_log.json read/write working |
| 7 | Night Agent | Quiz mode + Bedtime mode both working |
| 8 | Weekend Agent | Weekly Brain Upload delivered |
| 9 | Scheduler + Integration | All 3 pipelines automated on GitHub Actions |

**One rule: never start the next sprint until the current checkpoint passes.**
