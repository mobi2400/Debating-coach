import json
import re
import time
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
    from langchain_core.documents import Document
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    try:
        from langchain.schema import Document
    except ImportError:
        Document = None

try:
    from langchain_community.vectorstores import FAISS
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    FAISS = None

try:
    from langchain_chroma import Chroma
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    try:
        from langchain_community.vectorstores import Chroma
    except ImportError:
        Chroma = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    YouTubeTranscriptApi = None

from rag.chunking_strategy import get_splitter
from rag.embeddings import EMBEDDING_MAP

BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE_DIR / "chroma"
FAISS_DIR = BASE_DIR / "faiss"
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
    "english_vocab": "english_db",
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

    if doc_type == "english_vocab":
        try:
            from rag.wpm_extractor import extract_word_power

            return extract_word_power(path, doc_type=doc_type)
        except Exception as exc:
            print(f"[Ingest PDF] Structured english_vocab extractor failed for {path}: {exc}")
            # fall through to generic chunking

    try:
        pdf = fitz.open(path)
        text = "\n".join(page.get_text() for page in pdf)
        return _chunk_text(text, doc_type, {"source_path": path, "doc_type": doc_type})
    except Exception as exc:
        print(f"[Ingest PDF] Error for {path}: {exc}")
        return []


CHANNEL_VIDEO_LIMIT = 25


def list_channel_videos(channel_url: str, limit: int = CHANNEL_VIDEO_LIMIT) -> list[str]:
    if requests is None:
        return []

    url = channel_url.rstrip("/")
    if not url.endswith("/videos"):
        url = f"{url}/videos"

    try:
        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
        )
        response.raise_for_status()
    except Exception as exc:
        print(f"[Ingest YouTube] Channel fetch failed for {channel_url}: {exc}")
        return []

    seen = []
    for match in re.finditer(r'"videoId":"([A-Za-z0-9_-]{11})"', response.text):
        vid = match.group(1)
        if vid not in seen:
            seen.append(vid)
        if len(seen) >= limit:
            break
    return seen


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


EMBED_BATCH_SIZE = 50
EMBED_BACKOFF_SECONDS = 60
EMBED_MAX_RETRIES = 6


def _faiss_from_documents_batched(documents, embedding, batch_size=EMBED_BATCH_SIZE):
    """Build a FAISS index in batches with quota-aware backoff."""
    head = documents[:batch_size]
    tail = documents[batch_size:]

    store = _embed_with_backoff(
        lambda: FAISS.from_documents(documents=head, embedding=embedding)
    )

    while tail:
        batch = tail[:batch_size]
        tail = tail[batch_size:]
        _embed_with_backoff(lambda: store.add_documents(batch))

    return store


def _embed_with_backoff(call):
    delay = EMBED_BACKOFF_SECONDS
    for attempt in range(EMBED_MAX_RETRIES):
        try:
            return call()
        except Exception as exc:
            msg = str(exc)
            if "RESOURCE_EXHAUSTED" not in msg and "429" not in msg:
                raise
            if attempt == EMBED_MAX_RETRIES - 1:
                raise
            print(f"[Ingest] embedding quota hit, sleeping {delay}s (attempt {attempt + 1})")
            time.sleep(delay)
            delay = min(delay * 2, 300)
    return None


def build_knowledge_base(all_docs: list[dict]) -> dict:
    if FAISS is None and Chroma is None:
        return {}

    grouped_docs = {"knowledge_db": [], "style_db": [], "reasoning_db": [], "english_db": []}
    for doc in all_docs:
        grouped_docs[_resolve_store_name(doc["doc_type"])].extend(doc["documents"])

    stores = {}
    for store_name, documents in grouped_docs.items():
        if not documents:
            continue

        if FAISS is not None:
            persist_dir = FAISS_DIR / store_name
            persist_dir.mkdir(parents=True, exist_ok=True)
            store = _faiss_from_documents_batched(
                documents=documents,
                embedding=EMBEDDING_MAP[store_name],
            )
            store.save_local(str(persist_dir))
            stores[store_name] = store
        else:
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


def validate_sources(sources: dict) -> list[str]:
    issues = []

    for pdf in sources.get("pdfs", []):
        if "path" not in pdf or "doc_type" not in pdf:
            issues.append(f"Invalid PDF source entry: {pdf}")
            continue
        pdf_path = BASE_DIR / pdf["path"]
        if not pdf_path.exists():
            issues.append(f"Missing PDF source file: {pdf['path']}")

    for website in sources.get("websites", []):
        if "url" not in website or "site_type" not in website:
            issues.append(f"Invalid website source entry: {website}")

    for video in sources.get("youtube", []):
        if "channel_type" not in video:
            issues.append(f"Invalid YouTube source entry: {video}")
            continue
        if "video_id" not in video and "channel_url" not in video:
            issues.append(f"Invalid YouTube source entry: {video}")

    return issues


def run_ingest() -> dict:
    sources = load_sources()
    issues = validate_sources(sources)
    for issue in issues:
        print(f"[Sources] {issue}")

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
        channel_type = video.get("channel_type")
        if not channel_type:
            continue

        if "video_id" in video:
            video_ids = [video["video_id"]]
        elif "channel_url" in video:
            video_ids = list_channel_videos(video["channel_url"])
            if not video_ids:
                print(f"[Sources] No videos found for channel {video['channel_url']}")
        else:
            continue

        for vid in video_ids:
            all_docs.append(
                {
                    "doc_type": channel_type,
                    "documents": ingest_youtube(vid, channel_type),
                }
            )

    return build_knowledge_base(all_docs)


if __name__ == "__main__":
    stores = run_ingest()
    print(f"Built stores: {sorted(stores.keys())}")
