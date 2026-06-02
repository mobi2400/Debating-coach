try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    HuggingFaceEmbeddings = None


class MissingEmbeddings:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def embed_documents(self, _: list[str]):
        raise RuntimeError(
            f"Embeddings model '{self.model_name}' is unavailable. Install the sentence "
            "transformer dependencies from requirements.txt before building the vector stores."
        )

    def embed_query(self, _: str):
        raise RuntimeError(
            f"Embeddings model '{self.model_name}' is unavailable. Install the sentence "
            "transformer dependencies from requirements.txt before querying the vector stores."
        )


def _hf_embeddings(model_name: str):
    if HuggingFaceEmbeddings is None:
        return MissingEmbeddings(model_name)
    return HuggingFaceEmbeddings(model_name=model_name)


quality_embeddings = _hf_embeddings("sentence-transformers/all-mpnet-base-v2")
fast_embeddings = _hf_embeddings("sentence-transformers/all-MiniLM-L6-v2")
qa_embeddings = _hf_embeddings("sentence-transformers/multi-qa-mpnet-base-dot-v1")

EMBEDDING_MAP = {
    "knowledge_db": quality_embeddings,
    "style_db": fast_embeddings,
    "reasoning_db": qa_embeddings,
}
