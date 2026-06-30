from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONCEPTS_PATH = BASE_DIR / "debate_concepts.json"
CONTRACT_PATH = BASE_DIR / "debate_output_contract.json"

NODE_CONCEPT_MAP: dict[str, list[str]] = {
    "topic_foundation_node": ["core_principles", "argumentation", "framing"],
    "article_context_node": ["core_principles", "examples"],
    "topic_motion_mining_node": ["motions", "clash"],
    "motion_intelligence_node": ["motions", "clash", "burdens"],
    "motion_drafting_node": ["motions", "burdens", "clash"],
    "argue_node": ["argumentation", "burdens", "mechanism", "examples"],
    "coach_node": ["framing", "mechanism", "clash", "rebuttal", "weighing", "coach_notes"],
    "vocab_enrichment_node": ["core_principles"],
    "format_node": ["coach_notes", "clash", "weighing"],
    "delivery_node": [],
}

NODE_CONTRACT_MAP: dict[str, list[str]] = {
    "topic_foundation_node": ["meta", "shared_definitions", "nodes.topic_foundation_node"],
    "article_context_node": ["meta", "shared_definitions", "nodes.article_context_node"],
    "topic_motion_mining_node": ["meta", "nodes.topic_motion_mining_node"],
    "motion_intelligence_node": ["meta", "nodes.motion_intelligence_node"],
    "motion_drafting_node": ["meta", "shared_definitions", "nodes.motion_drafting_node"],
    "argue_node": ["meta", "shared_definitions", "nodes.argue_node", "cross_node_guardrails"],
    "coach_node": ["meta", "shared_definitions", "nodes.coach_node", "cross_node_guardrails"],
    "vocab_enrichment_node": ["meta", "nodes.vocab_enrichment_node", "cross_node_guardrails"],
    "format_node": ["meta", "shared_definitions", "nodes.format_node", "cross_node_guardrails"],
    "delivery_node": ["meta", "nodes.delivery_node", "cross_node_guardrails"],
}

PROMPT_VIEW_MAP: dict[str, list[str]] = {
    "argument_generation": ["definition", "how_to_build_an_argument", "argument_types", "examples"],
    "framing_generation": ["definition", "levels", "common_framing_modes", "failure_modes"],
    "mechanism_generation": ["definition", "levels", "mechanism_checks", "failure_modes"],
    "motion_generation": ["definition", "motion_types", "balanced_motion_design", "motion_drafting_process"],
    "clash_generation": ["definition", "how_to_identify", "clash_types", "how_to_explain_clash", "how_to_win_clash"],
    "rebuttal_generation": ["definition", "rebuttal_types", "how_to_answer", "rebuttal_drills", "failure_modes"],
    "coach_note_generation": ["definition", "what_a_good_coach_note_should_do", "what_it_should_not_do", "recommended_structure"],
}


def _deep_copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


@lru_cache(maxsize=1)
def load_debate_concepts() -> dict[str, Any]:
    return json.loads(CONCEPTS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_debate_output_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def _select_path(source_name: str, path: str) -> Any:
    source = load_debate_concepts() if source_name == "concepts" else load_debate_output_contract()
    current: Any = source
    for key in path.split('.'):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return _deep_copy_json(current)


def _select_paths(source_name: str, paths: list[str]) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for path in paths:
        value = _select_path(source_name, path)
        if value is not None:
            selected[path] = value
    return selected


def get_node_guidance(node_name: str) -> dict[str, Any]:
    return {
        "concepts": _select_paths("concepts", NODE_CONCEPT_MAP.get(node_name, [])),
        "contract": _select_paths("contract", NODE_CONTRACT_MAP.get(node_name, [])),
    }


def get_prompt_view(view_name: str, concept_section: str) -> dict[str, Any]:
    concepts = load_debate_concepts()
    section = concepts.get(concept_section, {})
    if not isinstance(section, dict):
        return {}
    keys = PROMPT_VIEW_MAP.get(view_name, [])
    selected: dict[str, Any] = {}
    for key in keys:
        if key in section:
            selected[key] = _deep_copy_json(section[key])
    return selected


def build_guidance_context(node_name: str, *, max_chars: int = 4000) -> str:
    payload = get_node_guidance(node_name)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def build_targeted_context(node_name: str, sections: list[tuple[str, str]], *, max_chars: int = 3000) -> str:
    payload: dict[str, Any] = {"node": node_name, "sections": {}}
    for source_name, path in sections:
        if source_name not in {"concepts", "contract"}:
            continue
        value = _select_path(source_name, path)
        if value is not None:
            payload["sections"][f"{source_name}.{path}"] = value
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."
