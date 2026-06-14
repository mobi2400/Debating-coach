from __future__ import annotations

from core.topic_utils import topic_keywords, topic_name
from rag.metadata import infer_topic_family


def _topic_info_list(topic_info: dict, key: str, limit: int = 3) -> list[str]:
    values = topic_info.get(key, [])
    if not isinstance(values, list):
        return []
    cleaned = [str(item).strip() for item in values if str(item).strip()]
    return cleaned[:limit]


def _join_nonempty(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if str(part).strip()).strip()


def _base_terms(topic: str, lead_title: str, topic_info: dict) -> dict:
    keywords = topic_keywords(topic)
    frameworks = _topic_info_list(topic_info, "essential_theoretical_frameworks", 2)
    concepts = _topic_info_list(topic_info, "key_concepts_own_these_precisely", 3)
    mechanisms = _topic_info_list(topic_info, "the_mechanisms_to_understand", 2)
    live_cases = _topic_info_list(topic_info, "live_case_studies_with_analytical_value", 1)
    argument_angles = _topic_info_list(topic_info, "argument_angles_most_debaters_miss", 2)

    return {
        "keywords": keywords,
        "frameworks": frameworks,
        "concepts": concepts,
        "mechanisms": mechanisms,
        "live_cases": live_cases,
        "argument_angles": argument_angles,
        "lead_title": lead_title,
        "topic": topic,
    }


def build_query_plan(node_name: str, state: dict) -> dict:
    topic = topic_name(state.get("topic"))
    lead_case = state.get("lead_case", {}) or {}
    lead_title = str(lead_case.get("title", "")).strip()
    topic_info = state.get("topic_info", {}) or {}
    terms = _base_terms(topic, lead_title, topic_info)

    metadata_hints = {
        "topic_family": infer_topic_family(topic),
        "source_classes": [],
        "time_scope": None,
        "debate_utility": [],
    }
    plan = {
        "node_name": node_name,
        "intent": "reference",
        "topic": topic,
        "lead_title": lead_title,
        "topic_family": metadata_hints["topic_family"],
        "preferred_stores": [],
        "store_queries": {},
        "metadata_hints": metadata_hints,
    }

    base_topic = _join_nonempty([topic, lead_title, " ".join(terms["keywords"][:4])])

    if node_name == "rag_enrich_node":
        plan["intent"] = "background"
        plan["preferred_stores"] = ["knowledge_db", "reasoning_db"]
        plan["metadata_hints"].update(
            {
                "source_classes": ["domain_reference", "encyclopedic_background", "debate_theory"],
                "time_scope": "durable",
                "debate_utility": ["definition", "preknowledge", "mechanism", "history"],
            }
        )
        plan["store_queries"] = {
            "knowledge_db": _join_nonempty(
                [base_topic, "definition history background prerequisite concepts framework"]
            ),
            "reasoning_db": _join_nonempty(
                [topic, " ".join(terms["frameworks"]), " ".join(terms["mechanisms"]), "debate theory mechanism"]
            ),
        }
        return plan

    if node_name == "argue_node":
        plan["intent"] = "argument_generation"
        plan["preferred_stores"] = ["reasoning_db", "knowledge_db", "style_db"]
        plan["metadata_hints"].update(
            {
                "source_classes": ["debate_theory", "domain_reference", "article", "personal_style", "debate_style"],
                "debate_utility": ["mechanism", "clash", "rebuttal", "example", "framing"],
            }
        )
        plan["store_queries"] = {
            "knowledge_db": _join_nonempty(
                [base_topic, "case study comparative example precedent impact"]
            ),
            "reasoning_db": _join_nonempty(
                [
                    topic,
                    lead_title,
                    " ".join(terms["frameworks"]),
                    " ".join(terms["mechanisms"]),
                    " ".join(terms["argument_angles"]),
                    "burden clash rebuttal mechanism debate theory",
                ]
            ),
            "style_db": _join_nonempty([topic, lead_title, "framing weighing extension rebuttal"]),
        }
        return plan

    if node_name == "coach_node":
        plan["intent"] = "coaching"
        plan["preferred_stores"] = ["reasoning_db", "style_db", "knowledge_db"]
        plan["metadata_hints"].update(
            {
                "source_classes": ["debate_theory", "personal_style", "debate_style", "domain_reference"],
                "debate_utility": ["framing", "weighing", "rebuttal", "clash", "mechanism"],
            }
        )
        plan["store_queries"] = {
            "knowledge_db": _join_nonempty([base_topic, "comparative example precedent"]),
            "reasoning_db": _join_nonempty(
                [topic, lead_title, " ".join(terms["frameworks"]), "clash burden weighing rebuttal mechanism WUDC"]
            ),
            "style_db": _join_nonempty([topic, "judge language framing weighing extension"]),
        }
        return plan

    if node_name == "english_coach_node":
        plan["intent"] = "vocabulary"
        plan["preferred_stores"] = ["english_db"]
        plan["metadata_hints"].update(
            {
                "source_classes": ["vocabulary"],
                "time_scope": "durable",
                "debate_utility": ["vocabulary"],
            }
        )
        plan["store_queries"] = {
            "english_db": _join_nonempty(
                [topic, lead_title, "debate language precision rhetoric argument vocabulary"]
            )
        }
        return plan

    plan["preferred_stores"] = ["knowledge_db"]
    plan["store_queries"] = {"knowledge_db": base_topic}
    return plan
