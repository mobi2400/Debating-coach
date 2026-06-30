# Debate Guidance Pipeline Plan

## Goal
Turn `debate_concepts.json` and `debate_output_contract.json` into active runtime guidance instead of passive reference files.

## Design Rule
Do not dump the full JSON files into prompts. Each node should receive only the slices it needs.

## Implemented Loader
A new helper lives in [core/debate_guidance.py](C:/Users/mobas/OneDrive/Desktop/Debate Coach/core/debate_guidance.py).

It provides:
- `load_debate_concepts()`
- `load_debate_output_contract()`
- `get_node_guidance(node_name)`
- `get_prompt_view(view_name, concept_section)`
- `build_guidance_context(node_name, max_chars=4000)`
- `build_targeted_context(node_name, sections, max_chars=3000)`

## File Roles
`debate_concepts.json`
- conceptual source of truth
- explains framing, mechanism, clash, burdens, rebuttal, motion design, etc.

`debate_output_contract.json`
- execution rulebook
- explains what each node must do, must not do, required outputs, and quality checks

## Node Consumption Map
`topic_foundation_node`
- concepts: `core_principles`, `argumentation`, `framing`
- contract: `nodes.topic_foundation_node`

`article_context_node`
- concepts: `core_principles`, `examples`
- contract: `nodes.article_context_node`

`topic_motion_mining_node`
- concepts: `motions`, `clash`
- contract: `nodes.topic_motion_mining_node`

`motion_intelligence_node`
- concepts: `motions`, `clash`, `burdens`
- contract: `nodes.motion_intelligence_node`

`motion_drafting_node`
- concepts: `motions`, `burdens`, `clash`
- contract: `nodes.motion_drafting_node`

`argue_node`
- concepts: `argumentation`, `burdens`, `mechanism`, `examples`
- contract: `nodes.argue_node`, `cross_node_guardrails`

`coach_node`
- concepts: `framing`, `mechanism`, `clash`, `rebuttal`, `weighing`, `coach_notes`
- contract: `nodes.coach_node`, `cross_node_guardrails`

`vocab_enrichment_node`
- concepts: `core_principles`
- contract: `nodes.vocab_enrichment_node`

`format_node`
- concepts: `coach_notes`, `clash`, `weighing`
- contract: `nodes.format_node`, `cross_node_guardrails`

`delivery`
- contract: `nodes.delivery_node`

## Prompt Strategy
Use one of two modes.

### 1. Node Guidance Context
Use `build_guidance_context(node_name)` when a node needs a compact full bundle of its mapped guidance.

Best for:
- fallback prompts
- first-pass structured generation
- node-level audits

### 2. Targeted Prompt Slices
Use `build_targeted_context(node_name, sections=[...])` when a prompt needs only one or two specific concepts.

Examples:
- `argue_node`
  - `concepts.argumentation`
  - `contract.nodes.argue_node`
- `coach_node` framing prompt
  - `concepts.framing`
  - `contract.nodes.coach_node`
- `coach_node` clash prompt
  - `concepts.clash`
  - `contract.shared_definitions.clash_block`

## Recommended Integration Order
1. `coach_node`
Reason: biggest quality upside for framing, mechanism, clash, coach note.

2. `argue_node`
Reason: improves raw debate claims before teaching layers touch them.

3. `motion_drafting_node`
Reason: better motion balance and cleaner burdens.

4. `format_node`
Reason: makes final output obey the contract more strictly.

## Usage Pattern Inside Nodes
Pseudo-shape:

```python
from core.debate_guidance import build_targeted_context

guidance = build_targeted_context(
    "coach_node",
    sections=[
        ("concepts", "framing"),
        ("concepts", "mechanism"),
        ("contract", "nodes.coach_node"),
    ],
    max_chars=2500,
)
```

Then include `guidance` in the prompt as a bounded reference block.

## Hard Rules
- Never inject the full `debate_concepts.json` into prompts.
- Never inject the full `debate_output_contract.json` into prompts.
- Prefer section-level slices over node-level full bundles when possible.
- Keep guidance payloads short enough that article/context evidence still fits.
- Use the contract to enforce output shape, and the concepts file to improve reasoning quality.

## What This Fixes
- inconsistent meaning of framing/mechanism/clash across nodes
- generic meta-advice instead of concrete debate teaching
- output drift between argument generation, coaching, formatting, and delivery
- prompt bloat from large JSON files

## Next Implementation Pass
Wire `core/debate_guidance.py` into:
- `agents/argue_node.py`
- `agents/coach_node.py`
- `agents/motion_drafting_node.py`
- optionally `agents/format_node.py`

That is the best next step because those are the nodes where debate quality is most sensitive to conceptual precision.
