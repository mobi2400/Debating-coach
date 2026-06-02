try:
    from langchain.text_splitter import (
        RecursiveCharacterTextSplitter,
        SentenceTransformersTokenTextSplitter,
    )
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    RecursiveCharacterTextSplitter = None
    SentenceTransformersTokenTextSplitter = None


class MissingSplitter:
    def __init__(self, name: str):
        self.name = name

    def split_text(self, _: str):
        raise RuntimeError(
            f"Splitter '{self.name}' is unavailable. Install the LangChain text splitting "
            "dependencies from requirements.txt before using RAG ingestion."
        )


def _recursive_splitter(**kwargs):
    if RecursiveCharacterTextSplitter is None:
        return MissingSplitter("RecursiveCharacterTextSplitter")
    return RecursiveCharacterTextSplitter(**kwargs)


def _token_splitter(**kwargs):
    if SentenceTransformersTokenTextSplitter is None:
        return MissingSplitter("SentenceTransformersTokenTextSplitter")
    try:
        return SentenceTransformersTokenTextSplitter(**kwargs)
    except Exception as exc:  # pragma: no cover - environment-specific bootstrap failure
        return MissingSplitter(f"SentenceTransformersTokenTextSplitter ({exc})")


knowledge_splitter = _recursive_splitter(
    chunk_size=600,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " "],
    length_function=len,
    is_separator_regex=False,
)

style_splitter = _recursive_splitter(
    chunk_size=400,
    chunk_overlap=80,
    separators=["\n\n", "\n", ". ", "! ", "? "],
    length_function=len,
    is_separator_regex=False,
)

reasoning_splitter = _recursive_splitter(
    chunk_size=720,
    chunk_overlap=120,
    separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " "],
    length_function=len,
    is_separator_regex=False,
)

youtube_splitter = _recursive_splitter(
    chunk_size=300,
    chunk_overlap=60,
    separators=[" ", ""],
    length_function=len,
    is_separator_regex=False,
)

SPLITTER_MAP = {
    "topic_pdf": knowledge_splitter,
    "news": knowledge_splitter,
    "wikipedia": knowledge_splitter,
    "your_speech": style_splitter,
    "debate_format": style_splitter,
    "personal_notes": style_splitter,
    "debate_theory": reasoning_splitter,
    "rhetoric": reasoning_splitter,
    "argument_theory": reasoning_splitter,
    "youtube_debate": youtube_splitter,
    "youtube_ted": youtube_splitter,
}


def get_splitter(doc_type: str):
    return SPLITTER_MAP.get(doc_type, knowledge_splitter)
