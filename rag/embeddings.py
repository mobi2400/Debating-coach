import os

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    GoogleGenerativeAIEmbeddings = None


GEMINI_EMBED_MODEL = "models/gemini-embedding-001"


class MissingEmbeddings:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def embed_documents(self, _: list[str]):
        raise RuntimeError(
            f"Embeddings model '{self.model_name}' is unavailable. Install "
            "langchain-google-genai and set GOOGLE_API_KEY to enable Gemini embeddings."
        )

    def embed_query(self, _: str):
        raise RuntimeError(
            f"Embeddings model '{self.model_name}' is unavailable. Install "
            "langchain-google-genai and set GOOGLE_API_KEY to enable Gemini embeddings."
        )


def _gemini_embeddings(task_type: str | None = None):
    if GoogleGenerativeAIEmbeddings is None:
        return MissingEmbeddings(f"{GEMINI_EMBED_MODEL} ({task_type or 'default'})")
    if not os.getenv("GOOGLE_API_KEY"):
        return MissingEmbeddings(f"{GEMINI_EMBED_MODEL} (GOOGLE_API_KEY not set)")
    try:
        kwargs = {"model": GEMINI_EMBED_MODEL}
        if task_type:
            kwargs["task_type"] = task_type
        return GoogleGenerativeAIEmbeddings(**kwargs)
    except Exception as exc:  # pragma: no cover - environment-specific bootstrap failure
        return MissingEmbeddings(f"{GEMINI_EMBED_MODEL} ({exc})")


quality_embeddings = _gemini_embeddings(task_type="retrieval_document")
fast_embeddings = _gemini_embeddings(task_type="semantic_similarity")
qa_embeddings = _gemini_embeddings(task_type="retrieval_query")

EMBEDDING_MAP = {
    "knowledge_db": quality_embeddings,
    "style_db": fast_embeddings,
    "reasoning_db": qa_embeddings,
    "english_db": fast_embeddings,
}


def embeddings_available(store_name: str) -> bool:
    return not isinstance(EMBEDDING_MAP.get(store_name), MissingEmbeddings)
