from __future__ import annotations

from rag.evidence_organizer import organize_evidence


def evaluate_query_plan(plan: dict, expected: dict) -> dict:
    preferred = list(plan.get("preferred_stores", []) or [])
    expected_stores = list(expected.get("preferred_stores", []) or [])
    store_score = 0.0
    if expected_stores:
        overlap = len(set(preferred) & set(expected_stores))
        store_score = overlap / len(expected_stores)

    query_blob = " ".join((plan.get("store_queries") or {}).values()).lower()
    required_terms = [term.lower() for term in (expected.get("required_terms") or [])]
    term_hits = sum(1 for term in required_terms if term in query_blob)
    term_score = term_hits / len(required_terms) if required_terms else 1.0

    hints = (plan.get("metadata_hints") or {})
    utility = set(hints.get("debate_utility") or [])
    source_classes = set(hints.get("source_classes") or [])
    expected_utility = set(expected.get("required_utility") or [])
    expected_classes = set(expected.get("required_source_classes") or [])
    utility_score = len(utility & expected_utility) / len(expected_utility) if expected_utility else 1.0
    class_score = len(source_classes & expected_classes) / len(expected_classes) if expected_classes else 1.0

    total = round((store_score + term_score + utility_score + class_score) / 4, 3)
    return {
        "store_score": round(store_score, 3),
        "term_score": round(term_score, 3),
        "utility_score": round(utility_score, 3),
        "class_score": round(class_score, 3),
        "total_score": total,
    }


def evaluate_structured_evidence(chunks_by_store: dict[str, list], expected_sections: list[str]) -> dict:
    organized = organize_evidence(chunks_by_store)
    present_sections = set(organized.keys())
    expected = set(expected_sections or [])
    section_score = len(present_sections & expected) / len(expected) if expected else 1.0
    return {
        "present_sections": sorted(present_sections),
        "expected_sections": sorted(expected),
        "section_score": round(section_score, 3),
    }
