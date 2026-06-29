# Agent Architecture Implementation Blueprint

This document is the implementation reference for the next major agent-architecture upgrade.

It turns the design decisions we discussed into an engineering guide that can be followed during refactoring.

The goal is not to throw away the current system.
The goal is to preserve what already works and improve the weak parts in a structured way.

This document is intentionally detailed so future implementation work can refer to one place instead of rethinking the architecture every time.

---

## 1. Core Intent

The upgraded system should feel less like a generic topic summary pipeline and more like a real debate training pipeline.

Today, the system already has useful strengths:

- topic selection
- research and ranking
- article/case selection
- RAG enrichment
- debate generation
- English/vocabulary support
- Telegram/WhatsApp formatting

But the architecture still has four major weaknesses:

1. topic pre-knowledge is too vague because one node tries to do too much
2. the debate lesson is often topic-led rather than motion-led
3. vocabulary repeats and is not always clearly taught
4. debate sections can sound buzzy or shallow instead of pedagogically strong

The new design fixes that by introducing:

- a motion intelligence track
- a two-layer pre-knowledge track
- a lesson-native vocabulary track
- a richer debate teaching structure that preserves the current learning sections

---

## 2. Current Architecture Snapshot

The current daily graph is defined in:

- [graph.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\graph.py)

Current order:

```text
research
-> filter
-> rank
-> lead_case_selector
-> preknowledge_enrichment
-> case_deep_dive
-> vocab_enrichment
-> summarize
-> argue
-> coach
-> english_coach
-> format
```

Current node files:

- [agents/research_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\research_node.py)
- [agents/filter_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\filter_node.py)
- [agents/rank_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\rank_node.py)
- [agents/lead_case_selector.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\lead_case_selector.py)
- [agents/preknowledge_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\preknowledge_enrichment_node.py)
- [agents/case_deep_dive_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\case_deep_dive_node.py)
- [agents/vocab_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\vocab_enrichment_node.py)
- [agents/summarize_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\summarize_node.py)
- [agents/argue_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\argue_node.py)
- [agents/coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\coach_node.py)
- [agents/english_coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\english_coach_node.py)
- [agents/format_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\format_node.py)

Likely supporting layers:

- [core/state.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\core\state.py)
- [memory/weekly_store.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\memory\weekly_store.py)
- [rag/retrieval_pipeline.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\retrieval_pipeline.py)
- [rag/retrieval_memory.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\retrieval_memory.py)
- [rag/query_planner.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\query_planner.py)
- [rag/query_router.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\query_router.py)
- [tools/rss_tool.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tools\rss_tool.py)
- [tools/tavily_tool.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tools\tavily_tool.py)
- [tools/wiki_tool.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tools\wiki_tool.py)
- [tools/ddg_tool.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tools\ddg_tool.py)

This means the main refactor surface is clear: the graph, the shared state, the pre-knowledge node, the debate-generation nodes, and the vocabulary logic.

---

## 3. Design Principles For The Refactor

Everything below should follow these principles.

### 3.1 Preserve useful output structure

Do not remove the current debate teaching sections if they are working for the user.

Preserve:

- for
- against
- clash
- mechanism
- framing
- rebuttal
- coach note

Upgrade their depth instead of replacing them.

### 3.2 Separate retrieval from reasoning

If one node fetches data, another node should analyze it.
Avoid nodes that both scrape, reason, summarize, and format in one step.

### 3.3 Use structured state, not loose text passing

Each node should return stable named fields.
This will reduce ambiguity, improve debuggability, and make formatting easier.

### 3.4 Use parallelism only where dependencies allow it

We should not parallelize for the sake of it.
We should parallelize only when two nodes depend on the same upstream input and do not need each other.

### 3.5 Motion should become the teaching spine

The final debate lesson should be built around a generated balanced motion grounded in the selected article.

### 3.6 Vocabulary should come from the lesson itself

The vocab node should not feel detached.
It should read the actual lesson material and extract 1-2 useful words from it.

---

## 4. Target Architecture Overview

### 4.1 High-level flow

```text
Topic Selection
   -> Parallel:
      - Topic Foundation Node
      - Topic Motion Mining Node
      - Article Discovery Node

Topic Motion Mining
   -> Motion Intelligence Node

Article Discovery
   -> Article Selection Node

After Article Selection
   -> Parallel:
      - Article Context Node
      - Motion Drafting Node

Then
   -> Article Explanation Node
   -> Debate Teaching Node
   -> Vocabulary Node
   -> Final Composition Node
```

### 4.2 Practical execution view

```text
Step 1:
- topic selected

Step 2 parallel:
- topic foundation
- topic motion mining
- article discovery

Step 3 sequential:
- motion mining -> motion intelligence
- article discovery -> article selection

Step 4 parallel:
- article context
- motion drafting

Step 5 sequential:
- article explanation
- debate teaching

Step 6:
- vocabulary extraction
- final composition
```

---

## 5. Node-by-Node Implementation Plan

This section describes the new or upgraded nodes, their responsibilities, their inputs, and their outputs.

### 5.1 Topic Selection Node

Purpose:
Pick the topic and normalize it for downstream work.

Possible current anchors:

- [agents/topic_selector.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\topic_selector.py)
- topic selection logic inside upstream run state or scheduler flow

Input:

- scheduler mode
- history
- manual override
- weekly learning state

Output contract:

```json
{
  "topic": "feminism",
  "topic_slug": "feminism",
  "topic_tags": ["gender", "rights", "social theory", "policy"],
  "search_queries": [
    "feminism debate motions",
    "feminism current affairs",
    "feminism policy conflict"
  ]
}
```

Implementation notes:

- normalize once here so every node receives the same topic object
- include search hints so downstream nodes avoid re-deriving queries differently

---

### 5.2 Topic Foundation Node

Purpose:
Build the foundational understanding of the topic itself.

This is the first pre-knowledge layer.

What it should teach:

- what the topic means
- key schools/frameworks
- important concepts
- major internal disagreements
- why it matters in debate

Suggested file:

- create `agents/topic_foundation_node.py`

Input:

```json
{
  "topic": "feminism",
  "topic_tags": ["gender", "rights"]
}
```

Output contract:

```json
{
  "topic_overview": "High-level explanation.",
  "key_frameworks": [
    {
      "name": "Liberal feminism",
      "explanation": "Focus on equal rights and access within institutions."
    }
  ],
  "key_concepts": [
    {
      "term": "intersectionality",
      "explanation": "How overlapping identities shape unequal experience."
    }
  ],
  "recurring_controversies": [
    "equality vs equity",
    "representation vs redistribution"
  ],
  "debate_relevance": "Why this topic repeatedly appears in debate."
}
```

Data sources:

- internal RAG theory materials
- Wikipedia-style source for basic factual orientation
- selective web support when theory context is thin

Important rule:

This node should not talk about today's specific article.
It is about the topic, not the case.

---

### 5.3 Topic Motion Mining Node

Purpose:
Collect 50-60 real motions on the chosen topic from motion sources.

Suggested file:

- create `agents/topic_motion_mining_node.py`

Input:

```json
{
  "topic": "feminism",
  "search_queries": ["feminism debate motions"]
}
```

Output contract:

```json
{
  "topic": "feminism",
  "motions_raw": ["..."],
  "motions_cleaned": ["..."],
  "source_sites": ["..."],
  "cache_key": "motions_feminism_v1",
  "fetched_at": "2026-06-30"
}
```

Implementation notes:

- keep this node retrieval-only
- store raw and cleaned results
- add per-topic caching to avoid repeated scraping
- save metadata like source and fetch time

Possible support modules:

- new motion source helper in `tools/`
- cache helper under `cache/` or `memory/`

Future option:

- support multiple motion websites and merge results into a normalized motion list

---

### 5.4 Motion Intelligence Node

Purpose:
Analyze the topic motion set and extract framing patterns.

Suggested file:

- create `agents/motion_intelligence_node.py`

Input:

```json
{
  "topic": "feminism",
  "motions_cleaned": ["..."]
}
```

Output contract:

```json
{
  "motion_types": ["policy", "value", "actor-based"],
  "common_framings": [
    "fairness and access",
    "autonomy vs protection"
  ],
  "prop_burdens": [
    "show structural harm",
    "prove intervention improves outcomes"
  ],
  "opp_burdens": [
    "show tradeoffs or implementation harm",
    "challenge the actor or mechanism"
  ],
  "common_clashes": [
    "freedom vs stability",
    "formal equality vs substantive equality"
  ],
  "balance_patterns": [
    "good motions narrow scope and actor",
    "bad motions become moral slogans"
  ],
  "drafting_guidance": {
    "preferred_scope": "clear actor, clear mechanism",
    "avoid_patterns": ["too broad", "too moralized", "one-sided wording"]
  }
}
```

Implementation notes:

- no scraping here
- this node should consume cached or fresh motion data from the mining node
- keep output structured so motion drafting can directly use it

---

### 5.5 Article Discovery Node

Purpose:
Find candidate current articles for the selected topic.

Current likely anchor:

- [agents/research_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\research_node.py)

Input:

```json
{
  "topic": "feminism",
  "search_queries": ["feminism current affairs"]
}
```

Output contract:

```json
{
  "candidate_articles": [
    {
      "title": "...",
      "url": "...",
      "source": "...",
      "published_at": "...",
      "summary_hint": "...",
      "relevance_score": 0.87,
      "debate_potential_score": 0.81
    }
  ]
}
```

Implementation notes:

- start this immediately after topic selection
- do not make it wait for motion analysis
- preserve current RSS, Tavily, DDG, and wiki support where useful

Expected refactor:

- existing `research -> filter -> rank` chain may remain, but should be re-framed as the article-discovery branch

---

### 5.6 Article Selection Node

Purpose:
Choose the final article for the day.

Current likely anchors:

- [agents/rank_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\rank_node.py)
- [agents/lead_case_selector.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\lead_case_selector.py)

Input:

```json
{
  "candidate_articles": ["..."]
}
```

Output contract:

```json
{
  "selected_article": {
    "title": "...",
    "url": "...",
    "source": "...",
    "published_at": "...",
    "body": "...",
    "selection_reason": "Fresh, rich in stakeholders, and debatable."
  }
}
```

Selection criteria:

- topic relevance
- freshness
- stakeholder richness
- clear tension
- enough material for both sides
- potential to become a balanced motion

Implementation note:

This node should explicitly optimize for debate potential, not just “most relevant article.”

---

### 5.7 Article Context Node

Purpose:
Build the second pre-knowledge layer, specific to the selected article.

Suggested file:

- create `agents/article_context_node.py`

Input:

```json
{
  "selected_article": {
    "title": "...",
    "body": "..."
  },
  "topic": "feminism"
}
```

Output contract:

```json
{
  "article_overview": "What happened in simple terms.",
  "stakeholders": [
    {
      "name": "government",
      "role": "decision-maker",
      "interest": "..."
    }
  ],
  "background_context": [
    "past policy context",
    "institutional context"
  ],
  "why_this_matters": "Why this story matters.",
  "live_tensions": [
    "rights vs implementation",
    "symbolic change vs material change"
  ]
}
```

Important rule:

This node is about understanding today's case before reading/debating it.
It should not duplicate topic foundation.

---

### 5.8 Motion Drafting Node

Purpose:
Use the selected article plus motion intelligence to draft a balanced motion.

Suggested file:

- create `agents/motion_drafting_node.py`

Input:

```json
{
  "selected_article": {
    "title": "...",
    "body": "..."
  },
  "motion_intelligence": {
    "common_framings": ["..."],
    "balance_patterns": ["..."]
  },
  "topic": "feminism"
}
```

Output contract:

```json
{
  "drafted_motion": "THBT ...",
  "motion_type": "policy",
  "actor": "state",
  "scope": "clear bounded scope",
  "prop_burden": [
    "must prove structural gain",
    "must defend actor and mechanism"
  ],
  "opp_burden": [
    "must show tradeoff, misfit, or better alternative"
  ],
  "likely_clash_axis": [
    "fairness vs feasibility",
    "symbolism vs material impact"
  ],
  "why_this_motion_is_balanced": "..."
}
```

This is one of the highest-value nodes in the whole redesign.

Why:

- it bridges real-world article selection with actual debate pedagogy
- it makes the lesson feel like a live motion, not a generic explainer

---

### 5.9 Article Explanation Node

Purpose:
Explain the selected article in plain language before the debate lesson starts.

Current likely anchor:

- [agents/case_deep_dive_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\case_deep_dive_node.py)

Input:

```json
{
  "selected_article": {
    "title": "...",
    "body": "..."
  },
  "article_context": {
    "stakeholders": ["..."]
  }
}
```

Output contract:

```json
{
  "plain_explanation": "...",
  "key_takeaways": ["..."],
  "article_examples_for_debate": ["..."]
}
```

Implementation notes:

- make this readable and concrete
- avoid sounding like a second summary node with vague phrasing
- its job is comprehension, not argument generation

---

### 5.10 Debate Teaching Node

Purpose:
Teach debate on the basis of the generated motion while preserving the current debate-learning structure.

Current likely anchors:

- [agents/argue_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\argue_node.py)
- [agents/coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\coach_node.py)
- [agents/summarize_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\summarize_node.py)

Input:

```json
{
  "topic_foundation": {"...": "..."},
  "article_context": {"...": "..."},
  "article_explanation": {"...": "..."},
  "drafted_motion": {"...": "..."},
  "rag_evidence": {"...": "..."}
}
```

Output contract:

```json
{
  "motion_explanation": "...",
  "prop_burden": ["..."],
  "opp_burden": ["..."],
  "for_arguments": [
    {
      "claim": "...",
      "explanation": "...",
      "mechanism": "...",
      "why_it_matters": "...",
      "article_example": "...",
      "likely_pushback": "...",
      "rebuttal": "..."
    }
  ],
  "against_arguments": [
    {
      "claim": "...",
      "explanation": "...",
      "mechanism": "...",
      "why_it_matters": "...",
      "article_example": "...",
      "likely_pushback": "...",
      "rebuttal": "..."
    }
  ],
  "core_clash": {
    "what_the_round_is_really_about": "...",
    "what_prop_must_win": "...",
    "what_opp_must_win": "..."
  },
  "mechanism": {
    "step_by_step_logic": ["..."]
  },
  "framing": {
    "prop_frame": "...",
    "opp_frame": "...",
    "strategic_note": "..."
  },
  "rebuttal_drills": [
    {
      "if_they_say": "...",
      "answer_with": "...",
      "why_that_answer_works": "..."
    }
  ],
  "coach_note": "..."
}
```

This node must preserve the current learning skeleton:

- for
- against
- clash
- mechanism
- framing
- rebuttal
- coach note

But it must add more depth:

- less buzzwording
- fewer repeated abstract terms
- more plain-language explanation
- article-grounded examples
- better burden explanation
- clear logic chains

Non-negotiable rule:

If the node uses technical debate words like:

- legitimacy
- burden
- framing
- mechanism
- principle
- comparative
- tradeoff

it must explain them in normal language within the section itself.

---

### 5.11 Vocabulary Node

Purpose:
Observe the final lesson and choose 1-2 useful words from the lesson material itself.

Current likely anchors:

- [agents/vocab_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\vocab_enrichment_node.py)
- [agents/english_coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\english_coach_node.py)

Input:

```json
{
  "topic_foundation": {"...": "..."},
  "article_context": {"...": "..."},
  "debate_teaching": {"...": "..."},
  "recent_vocab_history": ["..."]
}
```

Output contract:

```json
{
  "selected_words": [
    {
      "word": "legitimacy",
      "meaning": "The accepted right to exercise authority or power.",
      "why_it_helps": "Useful when arguing that a policy must be accepted as fair, not merely imposed.",
      "example": "A policy may improve efficiency but still lose legitimacy if the affected groups see it as unfair."
    }
  ]
}
```

Rules:

- only 1-2 words
- choose from actual lesson language first
- avoid repeated recent words
- avoid very basic filler words
- avoid obscure words that are hard to use in speech
- always provide one clear example

Important architecture decision:

This node should run late, after the debate lesson is drafted, because it needs to inspect the actual lesson language.

---

### 5.12 Final Composition Node

Purpose:
Format and assemble the final lesson in the right learning order.

Current likely anchor:

- [agents/format_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\format_node.py)

Input:

- all upstream structured outputs

Output:

- final delivery document
- delivery sections for Telegram / WhatsApp

Recommended order:

1. topic overview
2. topic foundation
3. article context
4. article explanation
5. generated motion
6. proposition burden
7. opposition burden
8. for arguments
9. against arguments
10. clash
11. mechanism
12. framing
13. rebuttal drills
14. coach note
15. vocabulary

Important rule:

This node should compose, not invent.
It should not be a second creative generation layer.

---

## 6. Parallel vs Sequential Design

This is the recommended execution model.

### 6.1 After topic selection

Run these in parallel:

- Topic Foundation Node
- Topic Motion Mining Node
- Article Discovery Node

Why:

- all three depend on the topic
- none of them depend on each other
- this is the highest-value safe parallelism

### 6.2 After motion mining

Run:

- Motion Intelligence Node

Why:

- it depends on the motion set
- it is analysis-only and should be decoupled from scraping

### 6.3 After article discovery

Run:

- Article Selection Node

Why:

- it depends on candidate article results

### 6.4 After article selection

Run these in parallel:

- Article Context Node
- Motion Drafting Node

Dependencies:

- Article Context needs selected article
- Motion Drafting needs selected article plus motion intelligence

### 6.5 After article context and motion drafting

Run sequentially:

- Article Explanation Node
- Debate Teaching Node

Why:

- the article should be understood before the debate lesson is fully formed
- the debate lesson depends on the motion and case context

### 6.6 Final step

Run:

- Vocabulary Node
- Final Composition Node

Why:

- vocab should inspect actual lesson content
- format should be last

---

## 7. Shared State Changes Needed

The current state layer will likely need a significant upgrade.

Primary candidate:

- [core/state.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\core\state.py)

The new state should move away from mostly free-form fields and include explicit structures such as:

```python
topic_info
topic_foundation
topic_motion_set
motion_intelligence
candidate_articles
selected_article
article_context
drafted_motion
article_explanation
debate_teaching
vocabulary_output
final_sections
```

Recommended implementation shape:

- add typed dictionaries or dataclasses where possible
- preserve backward compatibility during migration
- prefer additive migration instead of immediate destructive rename

Suggested migration approach:

1. add new fields first
2. let old and new nodes coexist briefly
3. migrate formatter and downstream consumers
4. remove old fields only after tests pass

---

## 8. RAG Responsibilities In The New Architecture

RAG should support the nodes where grounded context improves quality.

### 8.1 Topic Foundation

Use RAG for:

- conceptual definitions
- schools of thought
- theory references
- topic background

### 8.2 Article Context

Use RAG for:

- background context
- stakeholder history
- institutional setting
- issue-specific factual scaffolding

### 8.3 Motion Drafting

Use RAG for:

- examples of balanced motions
- matter-file-style framing
- patterns for actor, scope, and burden quality

### 8.4 Debate Teaching

Use RAG for:

- argument scaffolds
- matter files
- rhetoric books
- debate theory
- rebuttal models
- historical examples

### 8.5 Vocabulary

Use RAG lightly for:

- confirming definitions
- finding precise usage
- checking whether a word is debate-useful

RAG should not be overused for:

- formatting
- routing
- simple control flow
- message splitting

---

## 9. Caching And Memory Strategy

To improve efficiency, the system should cache topic-level artifacts and reuse them when possible.

### 9.1 Cache targets

Recommended cacheable assets:

- topic foundation outputs
- topic motion datasets
- motion intelligence outputs
- selected vocabulary history
- article metadata

### 9.2 Why this matters

If the same topic returns later, the system should not have to:

- rescrape all motions
- rebuild the same topic explanation
- repeat the same vocabulary choices

### 9.3 Possible storage locations

- `cache/`
- `memory/`
- a new small persistence helper module

Current related modules:

- [memory/weekly_store.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\memory\weekly_store.py)
- [rag/retrieval_memory.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\retrieval_memory.py)
- [rag/youtube_cache.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\rag\youtube_cache.py)

### 9.4 Memory-aware rules

The final system should be able to remember:

- recently used topics
- recently used motion styles
- recently taught vocabulary
- overused debate terms

This will reduce repetitive lessons.

---

## 10. Debate Pedagogy Rules

This section is important because content quality is not only an LLM problem.
It is an architecture problem plus a prompting problem.

### 10.1 Argument blocks must be full teaching blocks

Every main argument should ideally contain:

- claim
- explanation
- mechanism
- why it matters
- article-linked example
- likely pushback
- rebuttal response

### 10.2 Avoid buzzword-only output

If a section says:

- “this turns on legitimacy”
- “the burden is comparative”
- “the mechanism collapses”

that is not enough.

The node should unpack what those mean in plain language.

### 10.3 Reduce repeated abstract terms

Track and penalize repeated overuse of words like:

- principle
- incentive
- legitimacy
- tradeoff
- framing
- burden
- comparative

These words can still appear, but not as lazy placeholders.

### 10.4 Use article-grounded examples

Every major debate section should connect back to today's case when possible.

This makes the lesson feel:

- concrete
- memorable
- genuinely debatable

### 10.5 Preserve the current learning structure

The upgraded node must preserve:

- for
- against
- clash
- mechanism
- framing
- rebuttal
- coach note

The change is not “remove structure.”
The change is “add depth inside the structure.”

---

## 11. Vocabulary Quality Rules

### 11.1 Pick only 1-2 words

Retention matters more than volume.

### 11.2 Choose from lesson-native language first

Good vocab candidates should come from:

- the article explanation
- debate arguments
- clash/framing/rebuttal sections
- coach note

### 11.3 Definitions must be precise

Bad:

- “legitimacy means fairness”

Better:

- “legitimacy means the accepted right of an institution or authority to exercise power”

### 11.4 Give one useful example

The example should sound like something the learner can actually say in debate.

### 11.5 Avoid repetition

Use memory or a recent-history window to avoid the same small set of words appearing every day.

---

## 12. Likely File-Level Refactor Plan

This is the recommended engineering order.

### Phase 1: State and contracts

Likely files:

- [core/state.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\core\state.py)
- new schema helpers if needed

Tasks:

- add new structured fields
- define output contracts for each node
- avoid breaking the existing flow immediately

### Phase 2: Split pre-knowledge

Likely files:

- replace parts of [agents/preknowledge_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\preknowledge_enrichment_node.py)
- create:
  - `agents/topic_foundation_node.py`
  - `agents/article_context_node.py`

Tasks:

- separate topic foundation from article context
- keep current functionality alive while migrating

### Phase 3: Add motion track

Likely new files:

- `agents/topic_motion_mining_node.py`
- `agents/motion_intelligence_node.py`
- `agents/motion_drafting_node.py`

Tasks:

- create motion retrieval helpers
- add caching
- build pattern extraction
- generate article-grounded motion

### Phase 4: Rewire the graph

Likely file:

- [graph.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\graph.py)

Tasks:

- introduce parallel branches if LangGraph setup supports it
- otherwise simulate with deterministic staged execution first
- make article discovery independent from motion analysis wait time

### Phase 5: Upgrade debate teaching

Likely files:

- [agents/argue_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\argue_node.py)
- [agents/coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\coach_node.py)
- possibly [agents/summarize_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\summarize_node.py)

Tasks:

- preserve current section skeleton
- add richer argument schema
- unpack buzzwords
- inject article-specific examples
- improve rebuttal drill structure

### Phase 6: Upgrade vocabulary

Likely files:

- [agents/vocab_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\vocab_enrichment_node.py)
- [agents/english_coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\english_coach_node.py)

Tasks:

- make selection lesson-native
- cap to 1-2 words
- add recent-word memory filtering
- improve definition clarity

### Phase 7: Final formatting migration

Likely file:

- [agents/format_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\format_node.py)

Tasks:

- format using new structured outputs
- preserve delivery quality
- support section-by-section Telegram delivery
- keep WhatsApp constraints in mind

### Phase 8: Tests

Likely files:

- [tests/test_daily_e2e.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tests\test_daily_e2e.py)
- [tests/test_english.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tests\test_english.py)
- [tests/test_tools.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tests\test_tools.py)
- new tests for motion pipeline and state contracts

Tasks:

- assert section presence
- assert motion drafting quality structure
- assert vocab count limit
- assert pre-knowledge split
- assert no missing structured fields

---

## 13. Migration Strategy

Do not attempt a giant rewrite in one shot.

Recommended migration model:

1. add new state fields
2. introduce new nodes alongside old nodes
3. route output into formatter incrementally
4. preserve backward compatibility during transition
5. remove obsolete paths only after end-to-end tests pass

Why this matters:

- reduces regression risk
- keeps Telegram/WhatsApp outputs stable
- makes debugging easier

---

## 14. Success Criteria

The refactor is successful when the daily lesson clearly changes in the following ways:

### 14.1 Topic understanding

- topic pre-knowledge is more informative
- it teaches frameworks and concepts instead of vague lines

### 14.2 Article understanding

- article context explains stakeholders and tensions clearly
- the article feels easier to read because the learner is prepared

### 14.3 Motion realism

- a balanced motion is generated from the article
- the motion feels like something that could exist in real competitive debate

### 14.4 Debate pedagogy

- arguments are explained, not merely labeled
- rebuttals feel like drills
- buzzwords are unpacked
- article examples make the material concrete

### 14.5 Vocabulary quality

- only 1-2 words are taught
- definitions are precise
- examples are useful
- repetition drops noticeably

### 14.6 System efficiency

- topic-level caching reduces redundant fetches
- article discovery does not wait unnecessarily
- node responsibilities are clearer

---

## 15. Immediate First Implementation Tasks

If implementation starts now, the best first sequence is:

1. update [core/state.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\core\state.py) with new structured fields
2. split [agents/preknowledge_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\preknowledge_enrichment_node.py) into topic and article layers
3. add the motion track nodes
4. rewire [graph.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\graph.py) to support the new staged flow
5. refactor debate teaching outputs in [agents/argue_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\argue_node.py) and [agents/coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\coach_node.py)
6. refactor vocab selection in [agents/vocab_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\vocab_enrichment_node.py)
7. update [agents/format_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\format_node.py) last

That ordering minimizes breakage while still moving directly toward the new architecture.

---

## 16. Final Reminder

The point of this redesign is not just better architecture for its own sake.

It is to make the learner experience better:

- understand the topic properly
- understand the case properly
- see how real motions on that topic are framed
- debate a fresh motion built from a live article
- learn arguments in a clear and teachable way
- improve vocabulary without repetitive filler

If implementation choices later become unclear, prefer the path that improves:

- clarity
- teachability
- grounded debate realism
- low repetition
- maintainable node boundaries

That should be the guiding standard for every future refactor under this blueprint.
