import json
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    fitz = None

try:
    import requests
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    BeautifulSoup = None

try:
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    DefaultEmbeddingFunction = None

try:
    from langchain.schema import Document
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    Document = None

try:
    from langchain_community.vectorstores import Chroma
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    Chroma = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    YouTubeTranscriptApi = None

from rag.chunking_strategy import get_splitter
from rag.embeddings import EMBEDDING_MAP

BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE_DIR / "chroma"
SOURCES_FILE = BASE_DIR / "rag" / "sources.json"

STORE_ROUTING = {
    "topic_pdf": "knowledge_db",
    "news": "knowledge_db",
    "wikipedia": "knowledge_db",
    "your_speech": "style_db",
    "debate_format": "style_db",
    "personal_notes": "style_db",
    "debate_theory": "reasoning_db",
    "rhetoric": "reasoning_db",
    "argument_theory": "reasoning_db",
    "youtube_debate": "reasoning_db",
    "youtube_ted": "reasoning_db",
}


def _make_document(content: str, metadata: dict):
    if Document is None:
        return {"page_content": content, "metadata": metadata}
    return Document(page_content=content, metadata=metadata)


def _chunk_text(text: str, doc_type: str, metadata: dict) -> list:
    splitter = get_splitter(doc_type)
    chunks = splitter.split_text(text)
    return [_make_document(chunk, metadata) for chunk in chunks if chunk.strip()]


def ingest_pdf(path: str, doc_type: str) -> list:
    if fitz is None:
        return []

    try:
        pdf = fitz.open(path)
        text = "\n".join(page.get_text() for page in pdf)
        return _chunk_text(text, doc_type, {"source_path": path, "doc_type": doc_type})
    except Exception as exc:
        print(f"[Ingest PDF] Error for {path}: {exc}")
        return []


def ingest_youtube(video_id: str, channel_type: str) -> list:
    if YouTubeTranscriptApi is None:
        return []

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(chunk.get("text", "") for chunk in transcript)
        return _chunk_text(
            text,
            channel_type,
            {"video_id": video_id, "doc_type": channel_type},
        )
    except Exception as exc:
        print(f"[Ingest YouTube] Error for {video_id}: {exc}")
        return []


def ingest_website(url: str, site_type: str) -> list:
    if requests is None or BeautifulSoup is None:
        return []

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return _chunk_text(text, site_type, {"url": url, "doc_type": site_type})
    except Exception as exc:
        print(f"[Ingest Website] Error for {url}: {exc}")
        return []


def _resolve_store_name(doc_type: str) -> str:
    return STORE_ROUTING.get(doc_type, "knowledge_db")


def build_knowledge_base(all_docs: list[dict]) -> dict:
    if Chroma is None:
        return {}

    grouped_docs = {"knowledge_db": [], "style_db": [], "reasoning_db": []}
    for doc in all_docs:
        grouped_docs[_resolve_store_name(doc["doc_type"])].extend(doc["documents"])

    stores = {}
    for store_name, documents in grouped_docs.items():
        if not documents:
            continue

        persist_dir = CHROMA_DIR / store_name
        persist_dir.mkdir(parents=True, exist_ok=True)
        stores[store_name] = Chroma.from_documents(
            documents=documents,
            embedding=EMBEDDING_MAP[store_name],
            persist_directory=str(persist_dir),
        )

    return stores


def load_sources() -> dict:
    with open(SOURCES_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def run_ingest() -> dict:
    sources = load_sources()
    all_docs = []

    for pdf in sources.get("pdfs", []):
        all_docs.append(
            {
                "doc_type": pdf["doc_type"],
                "documents": ingest_pdf(pdf["path"], pdf["doc_type"]),
            }
        )

    for website in sources.get("websites", []):
        all_docs.append(
            {
                "doc_type": website["site_type"],
                "documents": ingest_website(website["url"], website["site_type"]),
            }
        )

    for video in sources.get("youtube", []):
        all_docs.append(
            {
                "doc_type": video["channel_type"],
                "documents": ingest_youtube(video["video_id"], video["channel_type"]),
            }
        )

    return build_knowledge_base(all_docs)


if __name__ == "__main__":
    stores = run_ingest()
    print(f"Built stores: {sorted(stores.keys())}")
