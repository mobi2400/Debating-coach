from functools import lru_cache
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

from rag.embeddings import EMBEDDING_MAP, embeddings_available
from rag.query_planner import build_query_plan

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


@lru_cache(maxsize=8)
def _load_vector_store(store_name: str):
    if store_name in BROKEN_STORES:
        return None

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

BROKEN_STORES: set[str] = set()


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
    if store_name in BROKEN_STORES or not embeddings_available(store_name):
        return None

    vector_store = _load_vector_store(store_name)
    if vector_store is None:
        return None

    mode = config["mode"]
    if mode == "hybrid":
        return build_hybrid_retriever(store_name, config["k"])

    search_kwargs = {key: value for key, value in config.items() if key != "mode"}
    return vector_store.as_retriever(search_type=mode, search_kwargs=search_kwargs)


def _coerce_utility(metadata: dict) -> list[str]:
    utilities = metadata.get("debate_utility") or []
    if isinstance(utilities, list):
        return [str(item).strip().lower() for item in utilities if str(item).strip()]
    if isinstance(utilities, str):
        return [utilities.strip().lower()] if utilities.strip() else []
    return []


def _chunk_score(chunk, query: str, plan: dict | None, store_name: str) -> int:
    content, metadata = _chunk_content(chunk)
    score = 0
    lowered_content = content.lower()
    query_terms = [term for term in query.lower().split() if len(term) > 3]

    for term in query_terms[:8]:
        if term in lowered_content:
            score += 2

    if not plan:
        return score

    hints = plan.get("metadata_hints", {}) or {}
    preferred_stores = plan.get("preferred_stores", []) or []
    if store_name in preferred_stores:
        score += 2

    source_class = str(metadata.get("source_class", "")).strip().lower()
    if source_class and source_class in {item.lower() for item in hints.get("source_classes", []) or []}:
        score += 3

    topic_family = str(metadata.get("topic_family", "")).strip().lower()
    hinted_family = str(hints.get("topic_family", "")).strip().lower()
    if topic_family and hinted_family and topic_family == hinted_family:
        score += 2

    time_scope = str(metadata.get("time_scope", "")).strip().lower()
    hinted_scope = str(hints.get("time_scope", "")).strip().lower()
    if time_scope and hinted_scope and time_scope == hinted_scope:
        score += 1

    utilities = set(_coerce_utility(metadata))
    desired_utilities = {str(item).strip().lower() for item in hints.get("debate_utility", []) or []}
    score += len(utilities & desired_utilities) * 2

    quality = str(metadata.get("source_quality", "")).strip().lower()
    if quality == "high":
        score += 2
    elif quality == "medium":
        score += 1

    return score


def _postprocess_chunks(chunks: list, query: str, plan: dict | None, store_name: str, limit: int) -> list:
    if not chunks:
        return []

    ranked = sorted(
        chunks,
        key=lambda chunk: _chunk_score(chunk, query, plan, store_name),
        reverse=True,
    )

    deduped = []
    seen = set()
    for chunk in ranked:
        content, _ = _chunk_content(chunk)
        signature = " ".join(content.lower().split())[:220]
        if not signature or signature in seen:
            continue
        seen.add(signature)
        deduped.append(chunk)
        if len(deduped) >= limit:
            break
    return deduped


def retrieve_for_node(node_name: str, query: str, state: dict | None = None, plan: dict | None = None) -> dict:
    """Returns {store_name: [chunks, ...]} so callers can preserve lane labels.

    Plain list iteration still works because `format_retrieved_context` accepts
    either a dict-of-lanes or a flat list.
    """
    if plan is None and state is not None:
        try:
            plan = build_query_plan(node_name, state)
        except Exception as exc:
            print(f"[Retrieval] query plan failed for {node_name}: {exc}")
            plan = None

    node_config = RETRIEVAL_CONFIG.get(node_name, {})
    retrieved: dict[str, list] = {}

    for store_name, config in node_config.items():
        preferred_stores = (plan or {}).get("preferred_stores", []) or []
        if preferred_stores and store_name not in preferred_stores:
            continue

        retriever = _build_retriever(store_name, config)
        if retriever is None:
            continue

        try:
            store_query = ((plan or {}).get("store_queries", {}) or {}).get(store_name, query)
            raw_chunks = retriever.invoke(store_query)
            limit = int(config.get("k") or len(raw_chunks) or 0)
            retrieved[store_name] = _postprocess_chunks(raw_chunks, store_query, plan, store_name, limit or len(raw_chunks))
        except Exception as exc:
            print(f"[Retrieval] {store_name} failed for {node_name}: {exc}")
            BROKEN_STORES.add(store_name)
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
