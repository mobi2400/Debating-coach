from typing import Optional, TypedDict


class AgentState(TypedDict):
    # Input
    topic: str
    selector_reason: str
    topic_info: dict
    topic_foundation: dict
    article_context: dict
    drafted_motion: dict
    debate_teaching: dict
    vocabulary_output: dict
    final_sections: dict

    # Research layer
    candidate_articles: list
    lead_case: dict
    lead_case_reason: str
    raw_articles: list
    reference_background: str
    article_background: str

    # RAG layer
    enriched_context: str
    preknowledge_notes: list
    article_context_notes: list
    case_deep_dive: list
    vocab_candidates: list
    vocab_context_notes: list
    topic_motion_set: dict
    motion_intelligence: dict

    # Filter + rank layer
    ranked_articles: list

    # Summarize layer
    summaries: list
    key_facts: list
    concepts: list

    # Argue layer
    arguments: dict

    # Coach layer
    debate_angle: str
    debate_packet: dict
    english_lesson: str
    vocab_words: list
    word_roots: list

    # Format layer
    final_doc: str

    # Router control
    task_type: str
    article_length: int
    retrieval_plans: dict
    retrieval_traces: dict

    # Night agent
    studied_today: Optional[bool]
    quiz_score: Optional[int]
