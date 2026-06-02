from pathlib import Path

try:
    from langchain_classic.retrievers import EnsembleRetriever
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    try:
        from langchain.retrievers import EnsembleRetriever
    except ImportError:
        EnsembleRetriever = None

try:
    from langchain_community.retrievers import BM25Retriever
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    BM25Retriever = None

try:
    from langchain_community.vectorstores import FAISS
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    FAISS = None

try:
    from langchain_community.vectorstores import Chroma
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    Chroma = None

from rag.embeddings import EMBEDDING_MAP

BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE_DIR / "chroma"
FAISS_DIR = BASE_DIR / "faiss"

RETRIEVAL_CONFIG = {
    "rag_enrich_node": {
        "knowledge_db": {"mode": "hybrid", "k": 6},
        "reasoning_db": {"mode": "mmr", "k": 4, "fetch_k": 25, "lambda_mult": 0.65},
    },
    "argue_node": {
        "knowledge_db": {"mode": "hybrid", "k": 3},
        "reasoning_db": {"mode": "mmr", "k": 5, "fetch_k": 25, "lambda_mult": 0.65},
        "style_db": {"mode": "similarity_score_threshold", "k": 2, "score_threshold": 0.72},
    },
    "coach_node": {
        "knowledge_db": {"mode": "hybrid", "k": 2},
        "reasoning_db": {"mode": "mmr", "k": 3, "fetch_k": 25, "lambda_mult": 0.65},
        "style_db": {"mode": "similarity_score_threshold", "k": 5, "score_threshold": 0.72},
    },
    "english_coach_node": {
        "english_db": {"mode": "similarity", "k": 6},
    },
}


def _load_vector_store(store_name: str):
    embedding = EMBEDDING_MAP.get(store_name)
    if embedding is None:
        return None

    faiss_dir = FAISS_DIR / store_name
    if FAISS is not None and faiss_dir.exists() and any(faiss_dir.iterdir()):
        try:
            return FAISS.load_local(
                str(faiss_dir),
                embedding,
                allow_dangerous_deserialization=True,
            )
        except Exception:
            pass

    if Chroma is not None:
        chroma_dir = CHROMA_DIR / store_name
        if chroma_dir.exists():
            return Chroma(
                persist_directory=str(chroma_dir),
                embedding_function=embedding,
            )

    return None


STORE_SECTION_LABELS = {
    "knowledge_db": "DOMAIN KNOWLEDGE",
    "reasoning_db": "DEBATE THEORY AND REASONING",
    "style_db": "YOUR DEBATE STYLE",
    "english_db": "ENGLISH VOCABULARY (Word Power Made Easy)",
}


def _vector_store_corpus(vector_store) -> tuple[list[str], list[dict]]:
    """Pull (texts, metadatas) from a FAISS or Chroma vector store for BM25."""
    # FAISS — read from docstore
    docstore = getattr(vector_store, "docstore", None)
    if docstore is not None and hasattr(docstore, "_dict"):
        texts, metadatas = [], []
        for document in docstore._dict.values():
            texts.append(document.page_content)
            metadatas.append(getattr(document, "metadata", {}) or {})
        return texts, metadatas

    # Chroma — get() returns {documents, metadatas}
    if hasattr(vector_store, "get"):
        try:
            data = vector_store.get()
            return list(data.get("documents") or []), list(data.get("metadatas") or [])
        except Exception:
            return [], []

    return [], []


def build_hybrid_retriever(store_name: str, k: int = 6):
    if EnsembleRetriever is None or BM25Retriever is None:
        return None

    vector_store = _load_vector_store(store_name)
    if vector_store is None:
        return None

    vector_retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )

    texts, metadatas = _vector_store_corpus(vector_store)
    if not texts:
        # No corpus available — degrade gracefully to vector-only retrieval.
        return vector_retriever

    bm25_retriever = BM25Retriever.from_texts(texts, metadatas=metadatas or None)
    bm25_retriever.k = k
    return EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[0.4, 0.6],
    )


def _build_retriever(store_name: str, config: dict):
    vector_store = _load_vector_store(store_name)
    if vector_store is None:
        return None

    mode = config["mode"]
    if mode == "hybrid":
        return build_hybrid_retriever(store_name, config["k"])

    search_kwargs = {key: value for key, value in config.items() if key != "mode"}
    return vector_store.as_retriever(search_type=mode, search_kwargs=search_kwargs)


def retrieve_for_node(node_name: str, query: str) -> dict:
    """Returns {store_name: [chunks, ...]} so callers can preserve lane labels.

    Plain list iteration still works because `format_retrieved_context` accepts
    either a dict-of-lanes or a flat list.
    """
    node_config = RETRIEVAL_CONFIG.get(node_name, {})
    retrieved: dict[str, list] = {}

    for store_name, config in node_config.items():
        retriever = _build_retriever(store_name, config)
        if retriever is None:
            continue

        try:
            retrieved[store_name] = retriever.invoke(query)
        except Exception as exc:
            print(f"[Retrieval] {store_name} failed for {node_name}: {exc}")
            retrieved[store_name] = []

    return retrieved


def _chunk_content(chunk) -> tuple[str, dict]:
    if hasattr(chunk, "page_content"):
        return chunk.page_content, getattr(chunk, "metadata", {}) or {}
    return chunk.get("page_content", ""), chunk.get("metadata", {}) or {}


def _format_lane(label: str, chunks: list) -> str:
    if not chunks:
        return ""
    lines = [f"{label}:"]
    for chunk in chunks:
        content, metadata = _chunk_content(chunk)
        source = (
            metadata.get("source_path")
            or metadata.get("url")
            or metadata.get("video_id")
            or "unknown"
        )
        lines.append(f"[source: {source}]\n{content}")
    return "\n---\n".join(lines)


def format_retrieved_context(chunks) -> str:
    """Format retrieved chunks for LLM prompts.

    Accepts the dict shape returned by `retrieve_for_node` (preferred — it
    keeps the per-lane DOMAIN KNOWLEDGE / DEBATE THEORY / YOUR DEBATE STYLE
    headers the prompts depend on) or a flat list (legacy callers).
    """
    if isinstance(chunks, dict):
        sections = []
        for store_name, store_chunks in chunks.items():
            label = STORE_SECTION_LABELS.get(store_name, store_name.upper())
            block = _format_lane(label, store_chunks)
            if block:
                sections.append(block)
        return "\n\n".join(sections).strip()

    return _format_lane("RETRIEVED CONTEXT", list(chunks)).strip()
