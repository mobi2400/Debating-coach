from __future__ import annotations


RETRIEVAL_EVAL_CASES = [
    {
        "name": "ir_argument_generation",
        "node_name": "argue_node",
        "state": {
            "topic": "international relations",
            "lead_case": {"title": "Ukraine sovereignty and NATO expansion"},
            "topic_info": {
                "essential_theoretical_frameworks": [
                    "Realism: states are rational actors pursuing survival in an anarchic system."
                ],
                "the_mechanisms_to_understand": [
                    "How the international system produces conflict even when no actor wants war - the security dilemma"
                ],
                "argument_angles_most_debaters_miss": [
                    "The double standard argument - when powerful states violate the norms they enforce on others"
                ],
            },
        },
        "expected": {
            "preferred_stores": ["reasoning_db", "knowledge_db", "style_db"],
            "required_terms": ["burden", "clash", "rebuttal", "mechanism"],
            "required_utility": ["mechanism", "rebuttal"],
            "required_source_classes": ["debate_theory", "domain_reference"],
        },
    },
    {
        "name": "preknowledge_foundation",
        "node_name": "rag_enrich_node",
        "state": {
            "topic": "feminism",
            "lead_case": {"title": "Gender equality and representation"},
            "topic_info": {
                "essential_theoretical_frameworks": [
                    "Liberal feminism focuses on equal rights within institutions."
                ],
                "key_concepts_own_these_precisely": [
                    "Intersectionality tracks how multiple structures of disadvantage overlap."
                ],
            },
        },
        "expected": {
            "preferred_stores": ["knowledge_db", "reasoning_db"],
            "required_terms": ["definition", "history", "background", "framework"],
            "required_utility": ["definition", "preknowledge"],
            "required_source_classes": ["domain_reference", "encyclopedic_background"],
        },
    },
    {
        "name": "coach_weighing",
        "node_name": "coach_node",
        "state": {
            "topic": "geopolitics",
            "lead_case": {"title": "China decoupling versus de-risking"},
            "topic_info": {
                "essential_theoretical_frameworks": [
                    "Balance of power explains why states hedge against dominance."
                ],
                "the_mechanisms_to_understand": [
                    "Deterrence and supply-chain leverage shape long-term state behaviour."
                ],
            },
        },
        "expected": {
            "preferred_stores": ["reasoning_db", "style_db", "knowledge_db"],
            "required_terms": ["clash", "burden", "weighing", "rebuttal"],
            "required_utility": ["framing", "weighing", "rebuttal"],
            "required_source_classes": ["debate_theory", "personal_style", "debate_style"],
        },
    },
]
