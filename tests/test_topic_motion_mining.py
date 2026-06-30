from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.topic_motion_mining_node import topic_motion_mining_node


def run_topic_motion_mining_test():
    state = {
        "topic": "feminism and gender",
        "topic_info": {
            "recurring_motions_at_wudc_level": [
                "THW implement gender quotas in all political institutions",
                "THBT feminism should prioritise economic equality over cultural change",
            ],
            "key_concepts_own_these_precisely": ["Intersectionality", "Patriarchy as a system"],
            "essential_theoretical_frameworks": ["Liberal feminism", "Intersectional feminism"],
            "live_case_studies_with_analytical_value": ["Workplace equality and representation"],
        },
    }
    result = topic_motion_mining_node(state)
    motion_set = result.get("topic_motion_set", {})
    assert motion_set.get("motions_cleaned"), "topic_motion_mining_node should produce motions"
    assert motion_set.get("source_sites"), "topic_motion_mining_node should record sources"
    print("Topic motion mining checks passed.")


if __name__ == "__main__":
    run_topic_motion_mining_test()
