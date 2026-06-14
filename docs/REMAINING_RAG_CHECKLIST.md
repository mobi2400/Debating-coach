# Remaining RAG Checklist

This file turns the remaining advanced-RAG discussion into an execution
checklist.

The goal is not just to list ideas.
The goal is to clarify:

- what is left
- why it matters
- how hard it is
- what risk it carries
- what order makes the most sense

---

## Current Status

Already implemented:

- query planning by node
- richer ingestion metadata
- hierarchical document preselection
- reranking
- context packing
- structured evidence lanes
- lightweight retrieval memory
- retrieval evaluation harness
- CLI retrieval evaluation mode

This means the project is already beyond basic chunk-search RAG.

What remains now is mostly about:

- measuring real lesson quality
- improving source selection quality
- making retrieval memory smarter
- expanding higher-value debate corpora

---

## Priority Ordering

Recommended order:

1. real trace-based evaluation from saved lessons
2. advanced YouTube ingestion with cached metadata
3. stronger retrieval memory with lesson similarity and source-performance reuse

After that:

4. better website/article extraction
5. cleaner explicit adaptive routing layer
6. external argument-example corpus integration

---

## 1. Real Trace-Based Evaluation

### Why this is first

Right now the eval harness is useful, but it is still mostly fixture-driven.
That means it tells us whether the architecture behaves as expected in designed
cases, but not whether the actual daily pipeline is retrieving the right material
in real lessons.

This is the most important next step because it changes evaluation from:

- “the planner looks correct”

to:

- “the real system is pulling good evidence for real lessons”

### What to build

- read recent saved lesson traces from `weekly_log.json`
- extract retrieval snapshots and retrieval traces
- score real lessons on:
  - lane diversity
  - source-class fit
  - duplicate rate
  - vocabulary freshness
  - debate usefulness heuristics
- print or save a compact report

### Suggested outputs

- average real-lesson retrieval score
- weakest node by retrieval quality
- repeated weak source refs
- repeated weak terms
- missing section types

### Files likely involved

- [memory/weekly_store.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\memory\weekly_store.py)
- [rag/retrieval_memory.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\retrieval_memory.py)
- [evals/rag/retrieval_eval.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\evals\rag\retrieval_eval.py)
- [main.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\main.py)

### Effort

- medium

### Risk

- low

### Payoff

- very high

### Checklist

- [ ] add reader for recent saved retrieval traces
- [ ] define scoring heuristics for real lessons
- [ ] add duplicate-rate checks
- [ ] add source-quality summary
- [ ] add CLI mode like `real-retrieval-eval`
- [ ] add tests for real-trace scoring

---

## 2. Advanced YouTube Ingestion With Cached Metadata

### Why this is second

This is the biggest source-quality expansion still pending.

If done well, it can provide:

- rebuttal patterns
- argument framing
- weighing language
- structure examples
- practice-round logic

If done badly, it creates transcript noise.

That is why it should come after real evals:
we want better visibility before expanding source complexity.

### What to build

A staged YouTube ingestion system that:

1. scans channel inventory
2. stores metadata cache
3. scores relevance from:
   - title
   - thumbnail text
   - description/about snippet
4. fetches transcripts only for relevant videos
5. ingests only selected transcripts into the reasoning lane

### Agreed design points from discussion

- initial scan should be broad, not just latest 1-2 videos
- metadata should be cached so future runs only process unseen videos
- thumbnail text should contribute to relevance scoring
- description/about snippet should contribute too
- full transcript fetch should happen only after relevance threshold

### Cache fields to store

- `video_id`
- `channel_name`
- `channel_url`
- `video_title`
- `thumbnail_url`
- `thumbnail_text`
- `description_snippet`
- `published_at`
- `selection_status`
- `selection_reason`
- `topic_tags`
- `argument_skills`
- `transcript_fetched`
- `ingest_status`

### Files likely involved

- [rag/ingest.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\ingest.py)
- [rag/metadata.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\metadata.py)
- new cache module under `rag/` or `cache/`
- possibly a new YouTube sync helper

### Effort

- high

### Risk

- medium

### Payoff

- very high

### Checklist

- [x] define per-channel cache format
- [x] add initial inventory scan
- [x] add incremental unseen-video scan logic
- [ ] add title/thumbnail/description relevance scoring
- [x] add transcript fetch gating
- [x] add transcript metadata enrichment
- [ ] route selected transcripts into `reasoning_db`
- [ ] add tests for cache reuse and selection logic

---

## 3. Better Retrieval Memory

### Why this is third

We already have lightweight retrieval memory.
That is a strong foundation.

What is still missing is a more intelligent notion of:

- which lessons were similar
- which source patterns were successful
- which query expansions were actually helpful

This upgrade matters because it moves memory from:

- “remember some prior terms”

to:

- “reuse retrieval strategies that historically improved lesson quality”

### What to build

- lesson similarity scoring
- retrieval win-pattern reuse
- source-performance summaries
- optional penalties for over-reused stale sources

### Strongest next behaviors

- find past lessons with overlapping topic-family and concepts
- reuse the best prior source refs when appropriate
- reuse successful query expansions
- avoid repeated weak/low-value sources

### Files likely involved

- [rag/retrieval_memory.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\retrieval_memory.py)
- [rag/query_planner.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\query_planner.py)
- [memory/weekly_store.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\memory\weekly_store.py)

### Effort

- medium

### Risk

- medium

### Payoff

- high

### Checklist

- [ ] add lesson similarity scoring
- [ ] track useful source refs across lessons
- [ ] track repeated low-value sources
- [ ] reuse high-performing query fragments more deliberately
- [ ] add freshness penalties for stale source overuse
- [ ] test memory reuse across similar topics

---

## 4. Better Website / Article Extraction

### Why this matters

The system still ingests websites fairly generically.
That means we may still embed:

- navigation noise
- repeated template text
- unrelated page fragments

This lowers embedding quality and retrieval precision.

### What to build

- stronger article-body extraction
- boilerplate removal
- duplicate block suppression
- cleaner text normalization before chunking

### Effort

- medium

### Risk

- low to medium

### Payoff

- medium to high

### Checklist

- [ ] add cleaner extraction for article body
- [ ] strip boilerplate/navigation/footer text
- [ ] add duplicate paragraph suppression
- [ ] benchmark before/after retrieval quality

---

## 5. Explicit Adaptive Routing Layer

### Why this is still left

We improved routing a lot through planner logic and node-specific configs.
But we have not yet split routing into a dedicated explicit layer.

That would make the architecture cleaner and easier to inspect.

### What to build

A dedicated routing layer that classifies retrieval intent into types like:

- definition
- preknowledge
- mechanism
- case evidence
- clash
- rebuttal
- style alignment
- vocabulary

### Effort

- medium

### Risk

- medium

### Payoff

- medium

### Checklist

- [ ] define router intent schema
- [ ] separate routing from planner logic
- [ ] connect node calls to router output
- [ ] add tests for routing decisions

---

## 6. External Argument-Example Corpus

### Why this is later

This is useful, but only after the core advanced RAG loop is stable.

We already decided that if an external argument dataset is added, it should be
treated as an example-pattern resource, not as factual evidence.

### Current short-listed direction

- `arguments-and-debates` style dataset as an argument-example bank

### What to build

- separate store for argument patterns
- keep it distinct from factual knowledge
- retrieve it mainly for:
  - `argue_node`
  - `coach_node`

### Effort

- medium

### Risk

- medium

### Payoff

- medium

### Checklist

- [ ] create separate argument-example lane
- [ ] define retrieval rules for example-pattern material
- [ ] avoid contaminating factual retrieval with synthetic examples
- [ ] test whether argument quality actually improves

---

## Effort / Risk / Payoff Table

| Item | Effort | Risk | Payoff |
|---|---|---|---|
| Real trace-based eval | Medium | Low | Very high |
| Advanced YouTube ingestion | High | Medium | Very high |
| Better retrieval memory | Medium | Medium | High |
| Better article extraction | Medium | Low-Medium | Medium-High |
| Explicit adaptive routing | Medium | Medium | Medium |
| External argument corpus | Medium | Medium | Medium |

---

## Recommended Execution Order

### Immediate next

1. real trace-based evaluation

### After that

2. advanced YouTube ingestion with cached metadata

### Then

3. better retrieval memory using lesson similarity and source-performance reuse

### Later cleanups / expansion

4. article extraction cleanup
5. explicit routing layer
6. external argument-example corpus

---

## Practical Summary

If the question is:

- “What is the smartest next thing to build?”

The answer is:

- real trace-based eval

If the question is:

- “What will most expand debate quality once the core is measured?”

The answer is:

- advanced YouTube ingestion

If the question is:

- “What will make the system smarter over time?”

The answer is:

- stronger retrieval memory

### YouTube phase status note

Current implementation status:

- title + description relevance scoring is implemented
- transcript fetch is now gated by relevance selection
- thumbnail text is part of the relevance layer
- OCR support is optional and only activates when the OCR dependency is available

That means the YouTube ingestion path is now smarter than blind transcript
fetching and can use thumbnail text as an additional ranking signal, while still
degrading safely in environments that do not yet have OCR installed.
