# Agent Architecture 3-Phase Plan

This document divides the architecture refactor into 3 implementation phases.

The purpose of this split is simple:

- avoid a risky all-at-once rewrite
- protect working delivery behavior
- build foundations first
- add the motion-driven learning layer second
- polish content quality and efficiency last

This file should be used together with:

- [AGENT_ARCHITECTURE_IMPLEMENTATION_BLUEPRINT.md](C:\Users\mobas\OneDrive\Desktop\Debate Coach\docs\AGENT_ARCHITECTURE_IMPLEMENTATION_BLUEPRINT.md)
- [AGENT_ARCHITECTURE_IMPLEMENTATION_GUARDRAILS.md](C:\Users\mobas\OneDrive\Desktop\Debate Coach\docs\AGENT_ARCHITECTURE_IMPLEMENTATION_GUARDRAILS.md)

---

## Phase 1: Foundation And State Refactor

### Goal

Create the architecture foundation without breaking the current daily pipeline.

This phase is about structure, contracts, and safe migration preparation.
It should not try to solve every content-quality issue at once.

### Main outcomes

- new structured state fields added
- old vague pre-knowledge path prepared for split
- graph prepared for staged branching
- tests updated for new state contracts

### Scope

1. Update shared state

Primary file:

- [core/state.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\core\state.py)

Add structured fields like:

- `topic_info`
- `topic_foundation`
- `topic_motion_set`
- `motion_intelligence`
- `candidate_articles`
- `selected_article`
- `article_context`
- `drafted_motion`
- `article_explanation`
- `debate_teaching`
- `vocabulary_output`
- `final_sections`

2. Split the current pre-knowledge responsibility in design

Current file:

- [agents/preknowledge_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\preknowledge_enrichment_node.py)

New target files:

- `agents/topic_foundation_node.py`
- `agents/article_context_node.py`

At the end of Phase 1, these nodes do not need to be perfect, but the split should exist clearly.

3. Rework graph staging

Primary file:

- [graph.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\graph.py)

Goal:

- prepare the graph for the new branch structure
- preserve compatibility where needed
- avoid forcing all nodes into one linear sequence

4. Add contract-aware tests

Likely files:

- [tests/test_daily_e2e.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tests\test_daily_e2e.py)
- new targeted tests for structured state outputs

### What not to do in Phase 1

- do not fully rewrite debate teaching yet
- do not tune vocabulary deeply yet
- do not overcomplicate graph parallelism before contracts are stable
- do not remove old compatibility paths too early

### Success criteria

- the system still runs
- new state fields exist
- topic foundation and article context are separated at the architecture level
- the graph is ready for the motion track to plug in next

---

## Phase 2: Motion-Driven Learning Pipeline

### Goal

Introduce the new motion intelligence architecture so the lesson becomes motion-led instead of just topic-led.

This is the highest-value product change in the whole redesign.

### Main outcomes

- real motions are collected for the topic
- those motions are analyzed for framing and balance
- a new balanced motion is drafted from the selected article
- article context and motion drafting work in parallel after article selection

### Scope

1. Add topic motion mining

New file:

- `agents/topic_motion_mining_node.py`

Purpose:

- collect 50-60 motions on the selected topic
- normalize and clean them
- cache them for reuse

2. Add motion intelligence

New file:

- `agents/motion_intelligence_node.py`

Purpose:

- analyze motion types
- detect common burdens
- identify common clash patterns
- learn what makes motions balanced or weak

3. Add motion drafting

New file:

- `agents/motion_drafting_node.py`

Purpose:

- use selected article plus motion intelligence
- generate a balanced motion for the lesson
- produce prop burden, opp burden, and likely clash axes

4. Upgrade article branch integration

Likely existing files:

- [agents/research_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\research_node.py)
- [agents/rank_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\rank_node.py)
- [agents/lead_case_selector.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\lead_case_selector.py)

Goal:

- preserve good article discovery behavior
- explicitly optimize selection for debate potential

5. Add article explanation flow

Likely file:

- [agents/case_deep_dive_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\case_deep_dive_node.py)

Goal:

- explain the article clearly before the debate lesson

### What not to do in Phase 2

- do not let motion drafting ignore motion intelligence
- do not let article context collapse back into topic theory
- do not make motion generation just a headline rewrite
- do not skip caching for motion mining

### Success criteria

- topic motions are mined and analyzed
- a balanced article-grounded motion is generated
- the lesson now has a real motion spine
- article context and motion generation are separate but connected

---

## Phase 3: Debate Quality, Vocabulary, And Delivery Polish

### Goal

Improve the actual teaching quality of the final lesson while keeping delivery stable.

This phase is where the learner experience should become noticeably better.

### Main outcomes

- debate sections are richer and less repetitive
- buzzwords are unpacked properly
- arguments are fully explained
- vocabulary is lesson-native, precise, and limited to 1-2 words
- final composition and delivery are polished

### Scope

1. Upgrade debate teaching

Likely files:

- [agents/argue_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\argue_node.py)
- [agents/coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\coach_node.py)
- possibly [agents/summarize_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\summarize_node.py)

Keep the current sections:

- for
- against
- clash
- mechanism
- framing
- rebuttal
- coach note

Add depth inside them:

- claim
- explanation
- mechanism
- why it matters
- article example
- likely pushback
- rebuttal response

2. Upgrade vocabulary

Likely files:

- [agents/vocab_enrichment_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\vocab_enrichment_node.py)
- [agents/english_coach_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\english_coach_node.py)

Goal:

- pick 1-2 words from the actual lesson
- avoid repetition using recent history
- define them clearly
- give one usable example each

3. Update final composition

Likely file:

- [agents/format_node.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\agents\format_node.py)

Goal:

- compose the new structured outputs cleanly
- preserve delivery quality
- keep Telegram and WhatsApp constraints safe

4. Add quality-focused tests

Likely files:

- [tests/test_daily_e2e.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tests\test_daily_e2e.py)
- [tests/test_english.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tests\test_english.py)
- new tests for motion output, vocab limits, and section structure

### What not to do in Phase 3

- do not add complexity only for style
- do not make the formatter invent missing content
- do not increase section length without improving clarity
- do not break delivery splitting while polishing content

### Success criteria

- debate sections teach, not just label
- repetitive buzzwording drops
- vocabulary feels fresh and useful
- final output is clearer, richer, and still deliverable

---

## Recommended Order Inside The 3 Phases

If implementation is done sequentially, the safest order is:

1. Phase 1
2. Phase 2
3. Phase 3

Do not start with Phase 3 first.

Why:

- without Phase 1, the architecture has no clean state/contracts
- without Phase 2, debate teaching still lacks the motion-driven backbone
- Phase 3 gives the biggest polish, but only after the system structure is right

---

## Fast Summary

### Phase 1

Build the skeleton.

- state
- node contracts
- pre-knowledge split
- graph preparation

### Phase 2

Build the motion engine.

- motion mining
- motion intelligence
- motion drafting
- article-context integration

### Phase 3

Polish the teaching.

- richer debate lesson
- better vocabulary
- stronger formatting and delivery
- final quality tests

---

## Final Rule

If a task feels unclear, classify it by this logic:

- if it changes state, contracts, or orchestration -> Phase 1
- if it changes motion realism or article-to-motion generation -> Phase 2
- if it changes teaching quality, wording, vocab, or final presentation -> Phase 3

That rule should keep implementation organized and prevent phase mixing.
