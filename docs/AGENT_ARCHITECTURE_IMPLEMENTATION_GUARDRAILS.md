# Agent Architecture Implementation Guardrails

This document explains what **not** to do while implementing the new agent architecture.

The main blueprint explains what to build.
This document explains the mistakes to avoid while building it.

It exists because large refactors often fail for avoidable reasons:

- mixing too many concerns into one node
- breaking working behavior while chasing new features
- introducing vague outputs again under new names
- overusing parallelism where dependencies are real
- adding complexity without improving learning quality

This file should be read alongside:

- [AGENT_ARCHITECTURE_IMPLEMENTATION_BLUEPRINT.md](C:\Users\mobas\OneDrive\Desktop\Debate Coach\docs\AGENT_ARCHITECTURE_IMPLEMENTATION_BLUEPRINT.md)

---

## 1. Do Not Break Working Output Structure Without Need

Do not remove the current debate learning skeleton just because we are upgrading the architecture.

Do not delete or collapse these sections unless there is a very strong reason:

- for
- against
- clash
- mechanism
- framing
- rebuttal
- coach note

Why this matters:

- the user is already familiar with this learning flow
- the problem is not the existence of these sections
- the problem is shallow content inside them

Correct approach:

- keep the sections
- improve their depth
- make them motion-led
- make them more explanatory

Wrong approach:

- replacing them with a new abstract format that looks clever but teaches less

---

## 2. Do Not Put Everything Into One “Smart” Node

Do not create one oversized node that:

- finds motions
- analyzes motions
- selects articles
- gathers context
- drafts a motion
- teaches debate
- chooses vocabulary

Why this is bad:

- impossible to debug
- impossible to test properly
- encourages vague prompt stuffing
- weakens cache reuse
- makes regressions harder to isolate

Correct approach:

- retrieval nodes fetch
- analysis nodes analyze
- teaching nodes teach
- formatting nodes format

---

## 3. Do Not Reintroduce Vague Pre-Knowledge

The old issue was that pre-knowledge tried to explain both the topic and the article at once, which produced vague output.

Do not recreate that failure under a new name.

Do not allow a single node to output generic lines like:

- “this topic is important in modern society”
- “many stakeholders are affected”
- “there are several debates around this issue”

Why this is bad:

- looks informative but teaches nothing
- wastes message space
- makes the lesson feel repetitive

Correct approach:

- topic foundation explains the topic itself
- article context explains this specific case
- each node has a narrow role

---

## 4. Do Not Make Motion Generation Detached From Real Motions

The whole point of the new motion track is to ground generated motions in real debate practice.

Do not generate a motion directly from the article without using the motion-intelligence layer.

Why this is bad:

- generated motions may become too broad
- they may become one-sided
- they may sound like article headlines, not debate motions
- they may ignore real burden and clash design

Correct approach:

- collect many real motions on the topic
- analyze framing and balance patterns
- then draft a new motion using those patterns plus the article

---

## 5. Do Not Scrape And Analyze In The Same Node If Avoidable

If a node is scraping motions or articles, do not also burden it with deep reasoning unless there is a strong implementation reason.

Why this is bad:

- hard to cache
- hard to retry safely
- hard to inspect intermediate output
- mixes unstable I/O with logic generation

Correct approach:

- one node fetches data
- another node consumes and analyzes it

This applies especially to:

- topic motion mining
- motion intelligence
- article discovery
- article context

---

## 6. Do Not Over-Parallelize

Parallelism is good only when dependency boundaries are clean.

Do not force nodes to run in parallel if one clearly depends on the other.

Examples of bad parallelism:

- drafting motion before motion intelligence exists
- generating final debate teaching before article context is ready
- choosing vocabulary before the lesson content exists

Why this is bad:

- produces race-condition-like logic issues
- leads to fallback junk values
- weakens lesson quality

Correct approach:

Safe parallel zones:

- topic foundation
- topic motion mining
- article discovery

And later:

- article context
- motion drafting

Everything else should follow dependency reality, not theoretical speed preference.

---

## 7. Do Not Pass Long Unstructured Paragraphs Between Nodes

Do not let nodes communicate only through giant text blobs when the content has structure.

Why this is dangerous:

- downstream nodes reinterpret upstream meaning inconsistently
- formatting logic becomes fragile
- debugging becomes guesswork
- tests become weak and fuzzy

Correct approach:

- pass structured fields
- keep names stable
- let the formatter consume structured outputs

Bad example:

```text
"Today’s topic is feminism. It is important because ... Here are some concepts ... maybe stakeholders include ..."
```

Better:

```json
{
  "topic_overview": "...",
  "key_frameworks": [...],
  "key_concepts": [...],
  "debate_relevance": "..."
}
```

---

## 8. Do Not Let The Formatter Invent Content

The formatting node should not act like a second creative model that rewrites or hallucinates missing logic.

Why this is dangerous:

- content quality becomes unpredictable
- missing upstream fields are silently masked
- bugs are harder to spot

Correct approach:

- upstream nodes generate content
- format node arranges it
- if upstream data is missing, fail clearly or degrade explicitly

The formatter should be a composer, not a secret co-author.

---

## 9. Do Not Let Debate Nodes Sound Smart At The Cost Of Teaching

One of the known issues is buzzword-heavy output.

Do not optimize prompts for “debate tone” alone.

Avoid outputs that repeatedly say things like:

- principle
- legitimacy
- incentive
- burden
- comparative
- framing
- tradeoff

without explaining them.

Why this is bad:

- sounds advanced
- teaches poorly
- creates daily repetition fatigue

Correct approach:

- technical terms are allowed
- but they must be unpacked in normal language
- every major argument needs logic, mechanism, and example

---

## 10. Do Not Treat Argument Labels As Full Arguments

Do not accept one-line outputs like:

- “this is about legitimacy”
- “this is about implementation tradeoffs”
- “the clash is fairness versus stability”

as a complete debate lesson.

Why this is insufficient:

- these are headings, not arguments
- a learner cannot reuse them in round
- they do not teach why the claim is true

Correct approach:

Each argument should explain:

- the claim
- why it is true
- how it happens
- why it matters
- how it connects to the article
- what the other side would say
- how to answer that

---

## 11. Do Not Make Vocabulary Detached From The Lesson

Do not pick vocab from a tiny static bank if the day’s lesson provides better words.

Do not choose words just because they are “fancy.”

Why this is bad:

- repetition becomes frequent
- words feel disconnected from the lesson
- the learner struggles to use them naturally

Correct approach:

- extract candidates from actual lesson material
- filter against recent history
- choose only 1-2
- define them precisely
- provide one usable example

---

## 12. Do Not Use Ambiguous Definitions In Vocabulary

Avoid definitions that are too loose.

Bad:

- “legitimacy means fairness”
- “nuance means detail”
- “framing means perspective”

Why this is bad:

- it teaches incomplete meaning
- learner misuses the word later

Correct approach:

- define clearly and precisely
- explain why the word is useful in debate
- give one example sentence the learner can actually use

---

## 13. Do Not Ignore Repetition Memory

Do not build the new nodes as if each day is isolated.

Why this is bad:

- same topic styles repeat
- same vocabulary repeats
- same buzzwords dominate
- user experience feels stale

Correct approach:

- use weekly memory and recent-history checks
- penalize repeated vocab
- penalize repeated framings
- rotate examples where possible

This is especially important for:

- vocabulary
- coach note language
- argument phrasing
- motion style diversity

---

## 14. Do Not Throw Away Existing RAG Strengths

The new architecture is not a reason to abandon what already works in retrieval.

Do not remove useful current strengths such as:

- multiple retrieval lanes
- reasoning retrieval
- English lane
- reranking
- memory-aware retrieval

Why this is important:

- the goal is to add better orchestration, not simplify into weaker retrieval
- quality comes from both architecture and evidence grounding

Correct approach:

- keep the current RAG strengths
- route them to more precise nodes
- make retrieval support the new structure better

---

## 15. Do Not Make RAG Fetch Everything For Every Node

Do not let every node independently call retrieval for nearly the same context.

Why this is bad:

- slower runs
- duplicate cost
- more noise
- harder trace inspection

Correct approach:

- retrieve with purpose
- store structured outputs
- reuse outputs downstream

Example:

- topic foundation retrieves topic theory once
- article context retrieves case context once
- debate teaching consumes both rather than rediscovering them from scratch

---

## 16. Do Not Skip Caching For Expensive Topic-Level Work

Motion mining is one of the clearest places where caching matters.

Do not scrape 50-60 motions again for the same topic if valid cached data exists.

Why this matters:

- reduces latency
- reduces failure risk
- reduces dependence on external websites
- makes repeated topics more stable

Correct approach:

- cache raw motions
- cache cleaned motions
- save fetch timestamps
- define a stale policy

---

## 17. Do Not Let Temporary Compatibility Become Permanent Mess

During migration, some old and new fields may coexist.

That is fine temporarily.

But do not let transitional compatibility layers become permanent architecture debt.

Why this matters:

- state becomes confusing
- duplicate logic accumulates
- formatter branches multiply

Correct approach:

- introduce compatibility intentionally
- mark temporary fields clearly
- remove old paths once tests and delivery are stable

---

## 18. Do Not Rewrite Everything Before Updating Tests

Do not leave tests behind while changing core contracts.

Why this is dangerous:

- regressions hide in formatting
- state mismatches slip through
- delivery failures appear late

Correct approach:

- update or add tests as each phase lands
- validate structured outputs
- validate section presence
- validate motion-drafting fields
- validate vocab limits

Especially important files:

- [tests/test_daily_e2e.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tests\test_daily_e2e.py)
- [tests/test_english.py](C:\Users\mobas\OneDrive\Desktop\Debate Coach\tests\test_english.py)
- retrieval and memory tests under `tests/`

---

## 19. Do Not Break Delivery Constraints While Improving Content

The lesson can become richer, but delivery constraints still matter.

Do not forget:

- Telegram section splitting behavior
- WhatsApp size limits
- readable section order
- message clarity

Why this matters:

- better content is useless if it fails to send
- long sections may trigger delivery problems

Correct approach:

- improve upstream content structure
- keep formatting and splitting disciplined
- test final delivery shape

---

## 20. Do Not Optimize Only For “Looks Better”

A prettier output is not enough if it is not more useful for learning.

Do not judge architecture changes only by:

- longer text
- fancier phrasing
- more sections
- more terminology

Judge them by whether the user can better:

- understand the topic
- understand the article
- understand the motion
- build arguments
- answer pushback
- learn new words they can actually use

This is the most important guardrail in the whole document.

---

## 21. Practical Red Flags During Implementation

If any of these start happening, pause and inspect the design:

- a node needs “just one more responsibility”
- formatter logic becomes content-generation logic
- the same topic explanation appears in article context
- article context starts teaching theory instead of context
- vocab words are selected before the debate lesson exists
- motion drafting ignores motion-analysis outputs
- every node calls RAG independently for similar information
- state fields become unclear or duplicated
- new prompts sound more impressive but teach less

These are not small issues.
They usually signal architectural drift.

---

## 22. Safe Default Decision Rule

When there is uncertainty during implementation, choose the option that improves:

- clarity
- teachability
- groundedness
- debuggability
- low repetition
- stable delivery

Do not choose the option merely because it is:

- more complex
- more agentic-sounding
- more parallel
- more prompt-heavy

The best version of this architecture is not the fanciest one.
It is the one that helps the learner think like a debater with the least confusion.
