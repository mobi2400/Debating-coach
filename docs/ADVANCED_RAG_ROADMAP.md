# Advanced RAG Roadmap For Debate Coach

This document explains:

1. where the current RAG system is strong
2. where it falls short compared to a more advanced RAG design
3. what architecture we should move toward
4. what improvements are in scope beyond retrieval alone
5. what questions we should settle before implementation

The goal is not to make the system "more complex" for its own sake.
The goal is to make the system:

- more accurate
- more debate-useful
- less repetitive
- easier to debug
- faster to improve over time

---

## 1. Why We Are Revisiting RAG

The current system already does more than a basic retrieval-augmented generation pipeline.
It is not a toy RAG setup.

Right now the project already has:

- multiple vector stores for different knowledge roles
- different chunking strategies by content type
- hybrid retrieval in `knowledge_db`
- MMR retrieval for theory and reasoning diversity
- a dedicated English lane
- memory that helps topic rotation and repetition control

That means the current system is already better than the common pattern:

`load files -> split everything the same way -> vector search -> dump chunks into prompt`

However, after comparing the project against advanced RAG patterns, the next bottleneck is clear:

the system still thinks mostly in terms of **retrieving chunks**, not **planning retrieval around the teaching goal**.

That difference matters because this project is not a chatbot for random questions.
It is a structured debate learning system.

So the next version of RAG should optimize for:

- one-topic-per-day teaching
- mechanism understanding
- debate framing
- durable memory
- context quality over raw retrieval quantity

---

## 2. Current RAG Architecture

### 2.1 Current retrieval lanes

The project currently uses four stores:

- `knowledge_db`
- `style_db`
- `reasoning_db`
- `english_db`

These are built in:

- [rag/ingest.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\ingest.py)
- [rag/retrieval_pipeline.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\retrieval_pipeline.py)
- [rag/chunking_strategy.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\chunking_strategy.py)

### 2.2 What each store currently does

#### `knowledge_db`

Used for:

- topic PDFs
- websites
- Wikipedia-like factual context
- broader case knowledge

Retrieval style:

- hybrid BM25 + dense retrieval

Why this is good:

- lexical matching catches exact terms
- vector similarity catches semantically related material

#### `reasoning_db`

Used for:

- debate theory
- rhetoric
- argumentation material
- YouTube transcript material

Retrieval style:

- MMR

Why this is good:

- prevents repetitive chunks
- helps get broader argumentative diversity

#### `style_db`

Used for:

- your own notes
- speeches
- style examples

Retrieval style:

- similarity threshold

Why this is good:

- does not force irrelevant style material into every prompt

#### `english_db`

Used for:

- vocabulary
- structured Word Power chunks

Why this is good:

- English retrieval is already more metadata-aware than the other stores

---

## 3. Current Strengths

Before discussing flaws, it is important to be precise about what is already working well.

### 3.1 Specialized lanes instead of one giant store

This is one of the best design choices in the current project.
It keeps:

- case knowledge
- debate theory
- personal style
- vocabulary

from contaminating each other.

### 3.2 Different chunking strategies by document type

This is a real advanced instinct already present in the code.
The project does not chunk a transcript the same way it chunks a debate theory PDF.

That is correct.

### 3.3 Hybrid retrieval already exists

The project is already beyond dense-only retrieval.
This matters for debate because exact terms like:

- sovereignty
- deterrence
- Westphalian
- intersectionality
- comparative advantage

often matter a lot.

### 3.4 Retrieval is already integrated into downstream teaching nodes

RAG is not just used once.
It is used to help:

- preknowledge
- argument generation
- coaching
- vocabulary enrichment

That is stronger than a shallow "retrieve once, summarize once" pipeline.

### 3.5 The project already has a memory mindset

Even though memory is not yet semantic retrieval memory, the system already uses:

- topic history
- vocabulary history
- study history
- quiz outcomes

This gives us a strong foundation for a smarter RAG later.

---

## 4. Current Gaps Compared To Advanced RAG

This section identifies the main limitations.

### 4.1 Retrieval and synthesis use the same chunks

Current pattern:

- split documents into chunks
- embed chunks
- retrieve chunks
- send chunks to the prompt

What is missing:

- document-level summary embeddings
- hierarchical retrieval
- separate "retrieval chunk" vs "generation chunk" logic

Why this matters:

A document may be highly relevant overall, but no single local chunk may match the query wording well enough.

For a debate system, that means:

- the best source may never be selected
- retrieved evidence may feel fragmented
- generation may lack global framing

### 4.2 Query rewriting is still weak

Current retrieval queries are handcrafted strings such as:

- topic name only
- `topic + prerequisites + framework`
- `topic + debate language framing`

This is useful, but limited.

What is missing:

- synonym expansion
- theory-name expansion
- concept decomposition
- case-aware query branching
- section-specific retrieval intent planning

Why this matters:

Debate questions are often asked in one vocabulary register and answered in another.
For example:

- "state coercion" may require retrieval about sanctions, deterrence, pressure, compliance, and power asymmetry
- "feminism" may require liberal feminism, radical feminism, intersectionality, reproductive labor, patriarchy, and structural exclusion

Without rewriting, recall suffers.

### 4.3 Routing is static by node, not adaptive by intent

Current architecture:

- `rag_enrich_node` retrieves fixed store mix
- `coach_node` retrieves fixed store mix
- `english_coach_node` retrieves fixed store mix

What is missing:

- route retrieval based on the kind of information needed

Examples of missing adaptive routing:

- definition query
- mechanism query
- rebuttal query
- theory query
- analogy query
- vocabulary query
- historical background query

Why this matters:

The same topic can require different retrieval behavior depending on what section we are building.

### 4.4 Metadata exists, but is not operational enough

Current metadata is mostly:

- `doc_type`
- `source_path`
- `url`
- `video_id`

English extraction is better because it also includes:

- `session`
- `chapter`
- `section_type`

What is missing:

- topic family
- durability
- source quality
- debate utility
- named frameworks
- named theorists
- argument function

Why this matters:

As the corpus grows, retrieval becomes noisier unless metadata is used to narrow the candidate pool.

### 4.5 No explicit lost-in-the-middle mitigation

The current pipeline formats retrieved chunks into prompt context, but it does not intentionally pack them for LLM reading behavior.

What is missing:

- context ordering by importance
- placement strategy for strong and weak evidence
- section-level prompt packing

Why this matters:

The best retrieved evidence can still be underused if it is buried in the middle of a long prompt.

### 4.6 No reranking stage

Right now retrieval output is not strongly reranked after initial retrieval.

What is missing:

- heuristic reranking
- metadata-aware reranking
- optional model-based reranking later

Why this matters:

Hybrid retrieval improves recall, but final top-k precision still needs refinement.

### 4.7 No semantic retrieval memory

The project has learning memory, but not retrieval memory.

Current memory supports:

- topic rotation
- vocab freshness
- night quiz follow-up

What is missing:

- cache of successful retrieval patterns
- reuse of prior good query expansions
- lesson-level retrieval trace reuse
- similarity lookup over prior taught lessons

Why this matters:

The project repeats retrieval work even when similar topics or similar questions have already been answered well.

### 4.8 No retrieval evaluation harness

Chunk sizes and embedding choices are currently thoughtful, but not formally measured against debate outcomes.

What is missing:

- test query set
- expected relevant sources
- expected relevant chunk types
- retrieval scoring metrics

Why this matters:

Without evaluation, future changes become guesswork.

---

## 5. Gap-To-Roadmap Table

| Gap | Current state | Why it matters | Priority | Proposed fix |
|---|---|---|---|---|
| No hierarchical retrieval | Chunk-level stores only | Best document may be missed; context is fragmented | P0 | Add document-summary index and two-stage retrieval |
| Weak query rewriting | Mostly template strings | Lower recall and poorer concept coverage | P0 | Add query planner with expansions and subqueries |
| Static node routing | Retrieval mix fixed per node | Same recipe used for different intents | P0 | Add intent-aware router |
| Underused metadata | Mostly descriptive metadata | Noisy retrieval as corpus grows | P0 | Add operational metadata and filters |
| No reranking | Raw retrieval goes to prompt | Lower precision in final chunks | P1 | Add reranker stage |
| No context packing | Chunks formatted but not strategically packed | LLM may miss strongest evidence | P1 | Add prompt context packer |
| No retrieval memory | Memory is curricular, not semantic | Repeated cost and inconsistent reuse | P1 | Add lesson retrieval cache and semantic lesson memory |
| No eval harness | Tuning is manual | Hard to know what actually improved | P1 | Build retrieval evals |
| Limited website cleanup | Generic page scraping | Embeddings may ingest noise | P2 | Improve article body extraction |
| No embedding benchmark | One model choice, little validation | Hard to know if embeddings fit debate best | P2 | Compare on internal eval set |

---

## 6. Target Architecture

The next-generation architecture should move from:

`topic -> retrieve chunks -> prompt`

to:

`topic -> plan -> route -> retrieve at the right level -> rerank -> pack -> teach`

That shift is the essence of the upgrade.

---

## 7. Proposed Next-Gen RAG Design

### 7.1 Query Planner

Add a planning layer before retrieval.

Suggested file:

- `rag/query_planner.py`

Responsibilities:

- normalize the topic and lead case
- detect the retrieval intent
- generate subqueries
- infer metadata filters
- allocate retrieval budget

Inputs:

- topic
- lead article title
- current node
- mode: daily / night / weekend
- optionally recent lesson memory

Outputs:

- canonical query
- synonyms
- theory expansions
- case expansions
- metadata hints
- lane-specific search plan

Example:

For topic `international relations` and case `Ukraine sovereignty`:

- foundational query:
  - `Westphalian sovereignty self-determination international law`
- mechanism query:
  - `security dilemma NATO expansion deterrence`
- rebuttal query:
  - `double standard humanitarian intervention precedent`

This is much stronger than one flat retrieval string.

### 7.2 Query Router

Add a router that chooses retrieval behavior based on intent.

Suggested file:

- `rag/query_router.py`

Intent labels could include:

- `definition`
- `preknowledge`
- `mechanism`
- `case_evidence`
- `clash`
- `rebuttal`
- `style_alignment`
- `vocabulary`
- `weekend_distillation`

Examples:

#### Preknowledge routing

- prioritize `knowledge_db`
- add `reasoning_db`
- filter for durable/foundational material

#### Debate build routing

- prioritize `reasoning_db`
- supplement with `knowledge_db`
- optionally use `style_db`

#### Vocabulary routing

- first extract from actual lesson material
- then enrich from `english_db`
- optionally supplement from external analytical prose

### 7.3 Multi-Level Retrieval

This is the biggest structural upgrade.

#### Level 1: Document retrieval

Create a document-summary index where each source document has:

- `document_id`
- short summary
- source type
- topic tags
- named concepts
- durability score
- debate usefulness score

Suggested file:

- `rag/document_index.py`

#### Level 2: Chunk retrieval

Once top documents are selected, retrieve chunks only from those documents.

This gives:

- better precision
- better global coherence
- lower noise

### 7.4 Metadata Enrichment

We should extend metadata at ingestion time.

Suggested new metadata fields:

- `topic_family`
- `source_class`
- `source_quality`
- `time_scope`
- `difficulty`
- `debate_utility`
- `named_frameworks`
- `named_theorists`
- `argument_role`
- `document_id`

Why ingestion-time metadata matters:

- metadata added late is expensive to patch
- metadata-aware retrieval depends on this foundation

### 7.5 Reranking Stage

Suggested file:

- `rag/reranker.py`

Initial reranking can be heuristic rather than model-heavy.

Possible rerank signals:

- metadata match with section intent
- lexical overlap
- theory-name overlap
- lead-case relevance
- source quality
- durability fit
- anti-duplication penalty

Later we can add:

- cross-encoder reranking
- LLM-based passage judging

### 7.6 Context Packer

Suggested file:

- `rag/context_packer.py`

Responsibilities:

- organize chunks by function
- sort by relevance and utility
- mitigate lost-in-the-middle
- format evidence blocks differently for each downstream node

Suggested packing logic:

- strongest passage early
- second strongest passage late
- support passages in the middle
- group by function:
  - definitions
  - mechanisms
  - examples
  - clash and rebuttal

### 7.7 Retrieval Memory

Suggested file:

- `rag/retrieval_memory.py`

This is different from `weekly_log.json`, but connected to it.

It should store:

- prior query plans
- winning retrieval expansions
- sources that produced strong lessons
- chunks used in final lessons
- whether those lessons led to successful recall later

This can eventually support:

- lower latency
- fewer repeated mistakes
- smarter topic continuation

### 7.8 Evaluation Harness

Suggested folder:

- `evals/rag/`

What we should measure:

- top-k precision
- top-k recall
- document recall
- chunk usefulness
- section-specific usefulness
- vocab freshness
- duplicate rate

This is what will let us improve with confidence.

---

## 8. How This Should Map To The Existing Project

### Existing files that should evolve

- [rag/ingest.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\ingest.py)
- [rag/retrieval_pipeline.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\retrieval_pipeline.py)
- [rag/chunking_strategy.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\chunking_strategy.py)
- [agents/rag_enrich_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\rag_enrich_node.py)
- [agents/preknowledge_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\preknowledge_enrichment_node.py)
- [agents/argue_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\argue_node.py)
- [agents/coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\coach_node.py)
- [agents/vocab_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\vocab_enrichment_node.py)
- [memory/weekly_store.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\memory\weekly_store.py)

### New files likely needed

- `rag/query_planner.py`
- `rag/query_router.py`
- `rag/document_index.py`
- `rag/reranker.py`
- `rag/context_packer.py`
- `rag/retrieval_memory.py`
- `evals/rag/test_queries.json`
- `evals/rag/expected_results.md`

---

## 9. Section-Specific Retrieval Design

Because this project produces structured learning output, different sections should retrieve differently.

### 9.1 Preknowledge section

Goal:

- explain what the user must know before reading the article

Needs:

- foundational definitions
- named frameworks
- basic historical context
- topic-specific prerequisites

Preferred retrieval:

- durable chunks
- foundational sources
- theory-aware background

### 9.2 Article / case section

Goal:

- explain the live case with enough background and analytical depth

Needs:

- top article summary
- comparative examples
- broader case context
- any relevant durable framework

Preferred retrieval:

- case-linked document summaries
- high-quality supporting chunks

### 9.3 Debate build section

Goal:

- produce actual argument material

Needs:

- mechanism explanation
- for/against warrants
- clash framing
- likely opposition responses
- weighing language

Preferred retrieval:

- theory-heavy chunks
- precedent and analogy chunks
- stylistic reinforcement from `style_db`

### 9.4 Vocabulary section

Goal:

- teach debate-useful English connected to today's lesson

Needs:

- words from the actual lesson material first
- then structured vocabulary grounding
- then debate-specific usage examples

Preferred retrieval flow:

1. extract words from drafted lesson
2. validate against context and freshness
3. support with `english_db`
4. optionally enrich via external serious analytical prose

### 9.5 Night quiz

Goal:

- reinforce what was actually taught

Needs:

- concepts actually used in lesson
- not generic topic trivia

Preferred retrieval:

- today's lesson artifacts
- today's retrieval trace
- today's vocab output

### 9.6 Weekend digest

Goal:

- preserve only what compounds

Needs:

- durable frameworks
- recurring mechanisms
- reusable examples
- repeat-use vocabulary

Preferred retrieval / filtering:

- remove breaking-only content
- prefer durable/high-utility metadata

---

## 10. Improvement Areas Beyond RAG

This project should not improve retrieval in isolation.
A better RAG will only matter if the downstream generation uses it well.

These are the additional areas worth improving after or alongside RAG.

### 10.1 Better retrieval-to-prompt contracts

Right now retrieved context is formatted as labeled chunk blocks.
That is useful, but still loose.

We should make each downstream node consume a more structured retrieval object:

- `definitions`
- `mechanisms`
- `examples`
- `theory`
- `style cues`
- `vocab cues`

That will reduce prompt ambiguity.

### 10.2 Better source-quality scoring

Not all sources deserve equal retrieval weight.

We should eventually score sources by:

- argumentative depth
- debate relevance
- recency value
- long-term usefulness
- clarity of prose

This is especially important because the system mixes:

- PDFs
- websites
- transcripts
- debate theory
- vocabulary books

### 10.3 Better website extraction

The current website ingestion is generic and may pick up:

- boilerplate
- navigation text
- unrelated page text

We should eventually improve:

- article-body extraction
- text cleanup
- duplicate removal
- source normalization

### 10.4 Retrieval observability

We need better debugging surfaces.

For each lesson, we should eventually know:

- what query was used
- which documents were selected
- why each chunk survived reranking
- which chunk appeared in which section

This will make bad outputs fixable instead of mysterious.

### 10.5 Output diversity and anti-repetition

Retrieval improvements should also reduce repeated:

- phrases
- sources
- examples
- frameworks
- vocab choices

But this may also require post-retrieval diversity controls.

### 10.6 Better alignment between RAG and pedagogy

The system should retrieve not just what is relevant, but what is teachable.

That means we should eventually distinguish:

- factual relevance
- debate usefulness
- beginner usefulness
- memory usefulness

This is one of the biggest philosophical upgrades we can make.

### 10.7 Advanced YouTube debate-channel ingestion

This deserves its own design because YouTube can become one of the most valuable
sources for:

- argument construction
- rebuttal method
- weighing language
- framing
- example usage
- round structure

But it can also become a noisy source if we ingest an entire channel blindly.

The right approach is not:

- fetch every video transcript
- embed everything
- hope retrieval figures it out later

The right approach is:

- scan channel inventory first
- score video usefulness from metadata
- fetch transcripts only for selected videos
- cache channel metadata so we do not repeatedly rescan the same content

#### 10.7.1 Proposed channel-scan policy

For each configured debate channel, the system should do:

1. initial broad scan of channel inventory
2. metadata extraction for each discovered video
3. metadata cache write
4. transcript fetch only for videos that pass debate-relevance threshold
5. later incremental refreshes that scan only for unseen videos

This is important because some channels contain:

- excellent workshops
- motion breakdowns
- practice rounds
- adjudication explanations
- announcements
- highlights
- registrations
- casual updates

Only some of those are useful for argument generation.

#### 10.7.2 Metadata we should collect before transcript fetch

For each video, we should collect and cache:

- `video_id`
- `channel_url`
- `channel_name`
- `video_title`
- `thumbnail_url`
- `thumbnail_text`
- `description_snippet`
- `published_at`
- `duration` if available
- `scan_timestamp`
- `transcript_available`
- `selection_status`
- `selection_reason`
- `video_kind`
- `topic_tags`
- `argument_skills`

The key design point is:

we should not need the transcript to decide whether a video is worth transcript ingestion.

#### 10.7.3 Initial scan depth

During the first run, we should scan a broader slice of the channel rather than
only the most recent handful of videos.

Recommended initial behavior:

- scan the latest `7-8 pages worth` of channel inventory if feasible
- or scan the latest `N` videos where `N` is a configurable upper bound

The exact implementation can depend on what metadata source is most stable, but
the product behavior should be:

- broad first-time inventory capture
- narrow incremental updates later

This is what the user wants operationally:

- full enough initial coverage to be useful
- no repetitive re-scanning cost
- only new/unseen videos scanned in future runs

#### 10.7.4 Incremental update policy

After the first scan, the system should not keep crawling the same videos again.

Instead:

1. load cached metadata manifest for the channel
2. scan current channel inventory
3. compare discovered `video_id`s against cached `video_id`s
4. keep existing metadata for already-seen videos
5. process only new/unseen videos
6. update cache manifest

This gives:

- lower latency
- lower network cost
- less ingestion noise
- predictable behavior in GitHub Actions

#### 10.7.5 Relevance scoring inputs

Each video should be scored using:

- title
- thumbnail text via OCR
- short video description / about snippet

This combination is better than title-only filtering because many useful debate
videos hide their true value in the thumbnail or short description.

Example:

- title: `Round 5`
- thumbnail: `HOW TO REBUT BETTER`
- description: `Workshop on weighing, burden, and comparative analysis`

Title alone is weak.
All three together are strong.

#### 10.7.6 Relevance scoring outputs

Each scanned video should be classified into a type such as:

- `debate_training`
- `practice_round`
- `motion_breakdown`
- `adjudication_analysis`
- `topic_background`
- `channel_noise`

It should also receive usefulness tags such as:

- `argument_generation`
- `rebuttal`
- `framing`
- `weighing`
- `extension`
- `example_bank`
- `style_learning`

These tags will later help retrieval target the right videos for the right node.

#### 10.7.7 Suggested cache structure

We should maintain a cache file per channel, for example:

- `cache/youtube_channels/<channel_slug>.json`

That cache should include:

- channel metadata
- last scan timestamp
- scan policy version
- array of discovered videos
- per-video metadata
- whether transcript was fetched
- whether transcript ingestion succeeded

This cache should become the source of truth for incremental channel ingestion.

#### 10.7.8 Suggested ingest flow for YouTube channels

The future pipeline should be:

1. discover channel inventory
2. collect video metadata
3. OCR thumbnail text
4. read short description/about snippet
5. classify debate relevance
6. skip non-useful videos
7. fetch transcript only for selected videos
8. chunk transcript with structured metadata
9. store selected chunks in `reasoning_db`

#### 10.7.9 Why this matters for downstream agents

If this is done correctly, agents like `argue_node` and `coach_node` will be able
to retrieve:

- better examples of how debaters actually frame arguments
- rebuttal patterns from real practice
- weighing language from strong speakers
- structure and explanation from teaching-oriented videos

That is much more useful than raw transcript dumping.

#### 10.7.10 Design implications before implementation

Before implementing this, we should decide:

- what initial scan depth should be
- where the metadata cache should live
- whether OCR should happen during initial scan or only for uncertain videos
- whether channel scanning should run during full ingest or in a separate sync step
- whether cached metadata should be committed, cached, or both

### 10.8 Argument analysis layer beyond RAG

There is a separate class of tooling that may not belong inside the retrieval
layer, but could still improve the debate system significantly.

Examples include:

- structured argument parsers
- Argdown-style argument analyzers
- claim-premise-objection mapping tools
- logical-structure validators
- argument graph environments

These tools are not primarily useful as **knowledge sources**.
They are more likely to be useful as **reasoning aids around node outputs**.

That means the right architectural question is not:

- should we ingest such repos into vector stores?

The better question is:

- can such tooling help us inspect, decompose, validate, or restructure the
  arguments generated by our nodes?

#### 10.8.1 Where this could fit

This kind of tooling would most likely live after retrieval and after initial
argument generation.

Possible flow:

`retrieval -> argue_node -> argument analysis layer -> coach_node -> format_node`

Or:

`retrieval -> argue_node -> structure validator -> revised argument package -> coach_node`

The key idea is:

- RAG brings evidence
- generation builds arguments
- analysis checks whether those arguments are well formed

#### 10.8.2 Nodes that could benefit most

##### `argue_node`

This is the strongest candidate.

Potential benefits:

- break arguments into claim, warrant, impact
- detect whether a point is descriptive rather than argumentative
- identify hidden assumptions
- identify likely rebuttal targets
- reduce repetition across for/against points

##### `coach_node`

Also a strong candidate.

Potential benefits:

- check whether the clash is genuine
- verify whether burdens are explicit
- identify whether rebuttals answer the mechanism or only the surface claim
- inspect whether weighing is comparative or generic

##### `night_agent` and quiz generation

Possible later application.

Potential benefits:

- ask questions about warrants and impacts, not just factual recall
- test whether the user understood hidden assumptions and rebuttal pressure

#### 10.8.3 What an argument analysis layer could do

If a suitable tool proves mature enough, it could help with:

- argument decomposition
- rebuttal target detection
- clash extraction
- structure scoring
- identifying weak warrants
- identifying unsupported impacts
- converting long argument prose into cleaner debate teaching blocks

This would help the system move from:

- fluent debate output

to:

- structurally inspectable debate output

#### 10.8.4 Why this is not a current implementation commitment

At the moment, this remains a **future exploration track**, not a committed
implementation step.

Reason:

- some repos in this space provide real parsing/analysis value
- others are mostly environment scaffolds or early-stage tooling
- we should not overfit the architecture around a tool before validating that it
  actually integrates cleanly and offers practical value

So this section exists to preserve the design idea:

- use argument-analysis tooling near the nodes
- do not treat it as a direct RAG corpus

#### 10.8.5 Status of this idea

Current status:

- worth remembering
- worth evaluating later
- not yet approved for implementation

If later evaluation shows a tool is genuinely useful, this can become a formal
Phase 4 or Phase 5 enhancement track.

### 10.9 External datasets and models worth evaluating

We also reviewed external assets from the DebateLabKIT Hugging Face
organization.

Reference:

- [DebateLabKIT on Hugging Face](https://huggingface.co/DebateLabKIT)

The conclusion from that review is intentionally conservative:

- only one dataset is worth considering for near-term use
- the rest should remain in a future-evaluation bucket

#### 10.9.1 Near-term dataset candidate

The only external dataset currently worth considering for near-term integration
is:

- `DebateLabKIT/arguments-and-debates`

Link:

- [DebateLabKIT/arguments-and-debates](https://huggingface.co/datasets/DebateLabKIT/arguments-and-debates)

Why this one stands out:

- it contains plain-text arguments and debates
- it appears directly relevant to pro/con reasoning
- it can potentially enrich the system with reusable debate argument patterns
- it is much closer to the current needs of `argue_node` and `coach_node` than
  the more formal argument-analysis datasets

How it should be treated if we later integrate it:

- as an **argument example bank**
- not as a factual evidence database
- not as a replacement for topic-specific source retrieval

That means if it is adopted later, it should likely live in a separate lane such
as an:

- `argument_examples_db`

rather than being merged directly into:

- `knowledge_db`

This is important because the role of this dataset would be:

- showing argument forms
- exposing reasoning patterns
- supporting for/against construction

not:

- providing authoritative factual evidence

#### 10.9.2 Future-evaluation bucket

The following DebateLabKIT assets should remain in the future bucket for now:

- `argdown_line-by-line`
- `deepa2-conversations`
- `deep-argmap-conversations`
- `argunauts-thinking`
- the `Argunaut` model family

Reason:

- they seem more useful for structured argument analysis, reasoning assistance,
  or model-training experiments
- they do not appear to be the best immediate fit for the current RAG upgrade
  track
- integrating them now would increase complexity before the core advanced-RAG
  foundation is settled

#### 10.9.3 Current design decision

The current agreed direction is:

- keep only `arguments-and-debates` on the shortlist
- leave all other DebateLabKIT datasets and models for later evaluation

This is not yet an implementation commitment.
It is a prioritization decision for future exploration.

---

## 11. Phased Roadmap

We should not implement everything at once.

### Phase 1: Foundation upgrades

Focus:

- query planner
- richer metadata
- metadata-aware routing

Why first:

- highest impact
- lowest disruption
- creates the base for everything else

### Phase 2: Better retrieval quality

Focus:

- document summary index
- two-stage retrieval
- reranking
- context packer

Why second:

- this is where retrieval quality jumps significantly

### Phase 3: Memory and evaluation

Focus:

- retrieval memory
- lesson retrieval traces
- evaluation harness
- benchmark queries

Why third:

- once the architecture is stable, we need reliable measurement

### Phase 4: Advanced optimization

Focus:

- embedding comparison
- model-based reranking
- smarter article extraction
- deeper adaptive routing

Why fourth:

- only worth doing once the rest is clean

---

## 12. Open Questions To Discuss Before Implementation

These are the questions we should settle together.

### 12.0 Discussion decisions already agreed

The following decisions have already emerged from our discussion and should be
treated as current design direction unless we explicitly revise them later.

#### Retrieval and architecture direction

- The project should move from basic chunk retrieval toward a more advanced RAG
  architecture.
- The next version should be designed around **teaching quality**, not just
  retrieval quantity.
- Retrieval should become more adaptive and section-aware rather than remaining
  static by node only.
- The best long-term direction is:
  - query planning
  - intent-aware routing
  - better metadata
  - multi-level retrieval
  - reranking
  - context packing
  - retrieval memory
  - evaluation

#### Debate-learning alignment

- The system should optimize for one-topic-per-day depth rather than broad
  shallow retrieval.
- The debate section is the most quality-sensitive section, so improvements in
  reasoning retrieval should prioritize `argue_node` and `coach_node`.
- Vocabulary should remain tightly connected to the actual lesson material, not
  drift into decorative dictionary-style word selection.
- The system should retrieve not only what is relevant, but what is actually
  teachable and debate-useful.

#### YouTube ingestion direction

- We should not blindly ingest every video from a debate channel.
- We should first inspect channel video metadata and only then decide whether to
  fetch transcripts.
- Relevance scoring should use:
  - title
  - thumbnail text
  - short description / about snippet
- Transcript fetch should happen only for selected videos.
- The first scan should be broader and should capture a meaningful slice of the
  channel rather than only a few recent videos.
- Channel metadata should be cached so future runs do not repeatedly rescan the
  same videos.
- Later scans should process only unseen videos.

#### External dataset direction

- From the DebateLabKIT Hugging Face organization, only
  `arguments-and-debates` remains on the shortlist for possible near-term use.
- If adopted, it should be treated as an argument-pattern resource, not a
  factual evidence corpus.
- The other DebateLabKIT datasets and models should remain in the future bucket
  until the core advanced-RAG foundation is complete.

#### Implementation philosophy

- We should discuss the design fully before implementation.
- The first implementation phase should focus on foundations rather than trying
  to build the entire advanced architecture at once.
- We should avoid building a system that is impressive in complexity but hard to
  debug or maintain.

### 12.0.1 Pending decisions

The following items are still open and should be finalized before we implement
the upgrade.

#### Retrieval design decisions

- What exact metadata schema should every ingested chunk support?
- What exact output contract should the query planner return?
- How much of query planning should be heuristic versus LLM-assisted?
- Should reranking begin as heuristic-only, or should we design an optional
  model-based reranker from day one?

#### Ingestion and indexing decisions

- Should document summaries be created at ingest time or lazily on first use?
- Should metadata enrichment be purely deterministic, or partially LLM-derived?
- How much structured metadata should be attached to transcript chunks?

#### YouTube-specific decisions

- What should the initial scan depth be for a newly added channel?
- Should OCR run on every scanned thumbnail or only when title/description are
  ambiguous?
- Where should the channel metadata cache live:
  - workspace file
  - GitHub Actions cache
  - committed artifact
  - or a hybrid arrangement?
- Should channel scanning happen inside the main ingest pipeline or in a
  dedicated pre-ingest sync step?

#### Memory and evaluation decisions

- How much retrieval trace should be saved per lesson?
- Should retrieval memory be lightweight and practical first, or more complete
  for later evaluation use?
- What evaluation set should we use to judge retrieval improvements?

### 12.1 How much complexity do we want in Phase 1?

Options:

- minimal planner with heuristics only
- planner with LLM support

Tradeoff:

- heuristics are cheaper and easier to debug
- LLM planning is more flexible but harder to control

### 12.2 Should document summaries be generated at ingest time or lazily?

Options:

- generate during ingest
- generate on first use and cache

Tradeoff:

- ingest-time summaries make retrieval fast later
- lazy summaries reduce upfront cost

### 12.3 Should metadata be rule-based or LLM-derived?

Options:

- rule-based tags only
- mixed rule-based + LLM-enriched tags

Tradeoff:

- rules are stable
- LLM tags are richer

### 12.4 How much retrieval trace should be stored in memory?

Options:

- lightweight trace only
- full chunk-level trace

Tradeoff:

- lightweight trace is cleaner
- full trace helps debugging and evaluation

### 12.5 Should vocabulary stay tightly lesson-native or remain partly curated?

My recommendation:

- lesson-native first
- English DB as support
- external search only as enrichment

This best fits the pedagogy of the project.

### 12.6 How much of the final architecture should rely on LLM reasoning versus deterministic rules?

This is an important philosophy decision.

For this project, the best approach is likely:

- deterministic where possible
- LLM where semantic expansion is genuinely needed

That preserves quality while keeping the pipeline debuggable.

---

## 13. Recommended Immediate Next Step

Before implementation, the best next move is:

1. review this design
2. finalize which metadata fields we want
3. finalize what the query planner should output
4. define Phase 1 scope precisely

Only after that should we begin coding.

The reason is simple:

if we implement before agreeing on planner shape and metadata shape, we will likely rewrite the retrieval layer twice.

---

## 14. Summary

The current project already has a strong RAG foundation.

Its next bottleneck is not "more data" or "more chunks."
Its next bottleneck is **retrieval intelligence**.

The future architecture should:

- plan retrieval before executing it
- route retrieval by intent
- retrieve at document level and chunk level
- use metadata operationally
- rerank evidence
- pack context strategically
- learn from past successful lessons
- measure itself through evaluation

If we do this carefully, the project should improve not just in factual retrieval quality, but in the specific thing that matters most:

producing better debate lessons.
