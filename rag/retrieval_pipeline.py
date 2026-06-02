from pathlib import Path

try:
    from langchain.retrievers import EnsembleRetriever
    from langchain_community.retrievers import BM25Retriever
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    EnsembleRetriever = None
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
    bm25_retriever = BM25Retriever.from_texts([])
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


def retrieve_for_node(node_name: str, query: str) -> list:
    node_config = RETRIEVAL_CONFIG.get(node_name, {})
    retrieved_chunks = []

    for store_name, config in node_config.items():
        retriever = _build_retriever(store_name, config)
        if retriever is None:
            continue

        try:
            retrieved_chunks.extend(retriever.invoke(query))
        except Exception as exc:
            print(f"[Retrieval] {store_name} failed for {node_name}: {exc}")

    return retrieved_chunks


def format_retrieved_context(chunks: list) -> str:
    formatted = []
    for index, chunk in enumerate(chunks, start=1):
        content = getattr(chunk, "page_content", chunk.get("page_content", ""))
        metadata = getattr(chunk, "metadata", chunk.get("metadata", {}))
        source_label = metadata.get("source_path") or metadata.get("url") or metadata.get(
            "video_id", "unknown"
        )
        formatted.append(f"[Chunk {index}] Source: {source_label}\n{content}")
    return "\n\n".join(formatted)
