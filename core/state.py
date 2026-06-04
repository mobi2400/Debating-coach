from typing import Optional, TypedDict


class AgentState(TypedDict):
    # Input
    topic: str
    selector_reason: str
    topic_info: dict

    # Research layer
    raw_articles: list
    reference_background: str

    # RAG layer
    enriched_context: str

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
    english_lesson: str
    vocab_words: list
    word_roots: list

    # Format layer
    final_doc: str

    # Router control
    task_type: str
    article_length: int

    # Night agent
    studied_today: Optional[bool]
    quiz_score: Optional[int]
