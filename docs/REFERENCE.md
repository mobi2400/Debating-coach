# DebateIQ Agent — Complete Technical Reference

> This file is the single source of truth for building the project. Every model string, every parameter, every function signature, every config value is defined here. When in doubt, check this file first.

---

## Table of Contents

1. [Repository Structure](#1-repository-structure)
2. [Dependencies](#2-dependencies)
3. [Environment Variables](#3-environment-variables)
4. [topics.json](#4-topicsjson)
5. [core/state.py](#5-corestatepy)
6. [core/llm_pool.py](#6-corellm_poolpy)
7. [core/llm_router.py](#7-corellm_routerpy)
8. [core/fallback.py](#8-corefallbackpy)
9. [tools/](#9-tools)
10. [rag/chunking_strategy.py](#10-ragchunking_strategypy)
11. [rag/embeddings.py](#11-ragembeddingspy)
12. [rag/ingest.py](#12-ragingestpy)
13. [rag/sources.json](#13-ragsourcesjson)
14. [rag/retrieval_pipeline.py](#14-ragretrieval_pipelinepy)
15. [agents/ — Daily Pipeline](#15-agents--daily-pipeline)
16. [agents/ — Night Agent](#16-agents--night-agent)
17. [agents/ — Weekend Agent](#17-agents--weekend-agent)
18. [memory/weekly_store.py](#18-memoryweekly_storepy)
19. [delivery/whatsapp.py](#19-deliverywhatsapppy)
20. [graph.py](#20-graphpy)
21. [main.py](#21-mainpy)
22. [.github/workflows/scheduler.yml](#22-githubworkflowsscheduleryml)
23. [Prompt Templates](#23-prompt-templates)
24. [RAG Retrieval Config](#24-rag-retrieval-config)
25. [WhatsApp Output Format](#25-whatsapp-output-format)
26. [Error Handling Rules](#26-error-handling-rules)
27. [Testing Checklist](#27-testing-checklist)

---

## 1. Repository Structure

```
debate-agent/
├── .github/
│   └── workflows/
│       └── scheduler.yml
├── agents/
│   ├── __init__.py
│   ├── research_node.py
│   ├── rag_enrich_node.py
│   ├── filter_node.py
│   ├── rank_node.py
│   ├── summarize_node.py
│   ├── argue_node.py
│   ├── coach_node.py
│   ├── format_node.py
│   ├── night_agent.py
│   └── weekend_agent.py
├── core/
│   ├── __init__.py
│   ├── state.py
│   ├── llm_pool.py
│   ├── llm_router.py
│   └── fallback.py
├── tools/
│   ├── __init__.py
│   ├── tavily_tool.py
│   ├── wiki_tool.py
│   ├── rss_tool.py
│   └── ddg_tool.py
├── rag/
│   ├── __init__.py
│   ├── chunking_strategy.py
│   ├── embeddings.py
│   ├── ingest.py
│   ├── retrieval_pipeline.py
│   └── sources.json
├── memory/
│   ├── __init__.py
│   ├── weekly_store.py
│   └── weekly_log.json
├── delivery/
│   ├── __init__.py
│   └── whatsapp.py
├── knowledge_base/
│   ├── pdfs/
│   │   ├── debate_frameworks/
│   │   ├── your_past_speeches/
│   │   ├── argument_theory/
│   │   └── topic_pdfs/
│   ├── websites/
│   └── youtube/
├── chroma/
│   ├── knowledge_db/
│   ├── style_db/
│   └── reasoning_db/
├── tests/
│   ├── test_router.py
│   ├── test_tools.py
│   ├── test_rag.py
│   ├── test_memory.py
│   └── test_weekend.py
├── graph.py
├── main.py
├── topics.json
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## 2. Dependencies

### requirements.txt

```
# LangChain + LangGraph
langchain==0.2.16
langchain-community==0.2.16
langchain-groq==0.1.9
langchain-google-genai==1.0.8
langgraph==0.2.28

# LLM Providers
groq==0.9.0
google-generativeai==0.7.2

# Research Tools
tavily-python==0.3.3
duckduckgo-search==6.2.13
feedparser==6.0.11
wikipedia==1.4.0
requests==2.32.3
beautifulsoup4==4.12.3

# RAG
chromadb==0.5.5
sentence-transformers==3.0.1
rank-bm25==0.2.2
PyMuPDF==1.24.10
youtube-transcript-api==0.6.2

# WhatsApp
twilio==9.2.3

# Utilities
python-dotenv==1.0.1
pydantic==2.8.2
aiohttp==3.10.5
```

### Install Command

```bash
pip install -r requirements.txt
```

---

## 3. Environment Variables

### .env File

```env
# Groq — get from console.groq.com (free)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Google Gemini — get from aistudio.google.com (free)
GOOGLE_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Tavily — get from tavily.com (free tier: 1000/month)
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Twilio — get from twilio.com (free sandbox)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
YOUR_WHATSAPP_NUMBER=whatsapp:+91XXXXXXXXXX

# Optional: set to "true" to skip WhatsApp and print to console during dev
DEV_MODE=false
```

### .gitignore

```
.env
chroma/
memory/weekly_log.json
__pycache__/
*.pyc
.DS_Store
*.egg-info/
dist/
build/
.venv/
venv/
```

### Loading in Code

```python
# Put this at the top of every file that needs env vars
from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
```

---

## 4. topics.json

```json
[
  "feminism",
  "geopolitics",
  "religion and society",
  "personal finance and economy",
  "climate change and environment"
]
```

Add or remove topics here. The daily pipeline iterates over every item in this list.

---

## 5. core/state.py

This is the shared state that flows through every LangGraph node. Every field must be defined here. No agent should add new keys to state — all keys are declared upfront.

```python
from typing import TypedDict, Optional

class AgentState(TypedDict):
    # Input
    topic: str                      # current topic being processed

    # Research layer
    raw_articles: list              # list of dicts from all 4 tools
                                    # each dict: {title, url, content, source, published}

    # RAG layer
    enriched_context: str           # formatted string from retrieve_for_node("rag_enrich_node")

    # Filter + Rank layer
    ranked_articles: list           # top 5-7 dicts after filter and rank

    # Summarize layer
    summaries: list                 # list of strings, one summary block per article
    key_facts: list                 # list of strings — facts tagged for memory
    concepts: list                  # list of strings — concepts tagged for Weekend Agent

    # Argue layer
    arguments: dict                 # keys: "for" (list), "against" (list), "middle" (str)

    # Coach layer
    debate_angle: str               # full coaching output as a single string

    # Format layer
    final_doc: str                  # compiled WhatsApp-ready message

    # Router control
    task_type: str                  # controls which LLM the router selects
    article_length: int             # if > 8000 chars, router uses long_ctx LLM

    # Night agent
    studied_today: Optional[bool]   # set by night agent after user replies
    quiz_score: Optional[int]       # percentage score after quiz
```

---

## 6. core/llm_pool.py

All LLM definitions live here. Never instantiate an LLM anywhere else in the codebase.

```python
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

LLM_POOL = {
    # Ultra-fast, simple tasks: filter, rank, dedup
    "fast": ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        max_tokens=2048,
        groq_api_key=os.getenv("GROQ_API_KEY")
    ),

    # High-quality summaries
    "balanced": ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=4096,
        groq_api_key=os.getenv("GROQ_API_KEY")
    ),

    # Structured output, JSON, formatting, quizzes
    "structured": ChatGroq(
        model="mixtral-8x7b-32768",
        temperature=0.1,
        max_tokens=4096,
        groq_api_key=os.getenv("GROQ_API_KEY")
    ),

    # Deep analytical reasoning, argument generation
    "reasoning": ChatGroq(
        model="deepseek-r1-distill-llama-70b",
        temperature=0.4,
        max_tokens=4096,
        groq_api_key=os.getenv("GROQ_API_KEY")
    ),

    # Long context — reads full articles up to 1M tokens
    "long_ctx": ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.2,
        max_output_tokens=4096,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    ),

    # Best reasoning quality — debate coaching only
    "best": ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0.5,
        max_output_tokens=4096,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    ),
}
```

---

## 7. core/llm_router.py

```python
from core.llm_pool import LLM_POOL
from core.state import AgentState

# Maps task_type string → LLM pool key
ROUTING_MAP = {
    "fetch":     "long_ctx",    # Gemini Flash — long article reading
    "filter":    "fast",        # Llama 8B — simple dedup
    "rank":      "fast",        # Llama 8B — simple scoring
    "summarize": "balanced",    # Llama 70B — quality summaries
    "argue":     "reasoning",   # DeepSeek R1 — deep argument analysis
    "debate":    "best",        # Gemini Pro — best coaching output
    "format":    "structured",  # Mixtral — clean structured output
    "quiz":      "structured",  # Mixtral — structured JSON quiz
    "bedtime":   "balanced",    # Llama 70B — quality compression
    "weekend":   "reasoning",   # DeepSeek R1 — analytical filtering
}

def route_by_task(state: AgentState) -> str:
    """Returns the LLM pool key for the current task."""
    task = state.get("task_type", "balanced")
    article_length = state.get("article_length", 0)

    # Override: very long articles always go to long_ctx
    if article_length > 8000:
        return "long_ctx"

    return ROUTING_MAP.get(task, "balanced")


def get_llm(state: AgentState):
    """Returns the LLM instance for the current state task_type."""
    key = route_by_task(state)
    return LLM_POOL[key]
```

---

## 8. core/fallback.py

```python
from core.llm_pool import LLM_POOL
from core.state import AgentState
from core.llm_router import route_by_task
import logging

logger = logging.getLogger(__name__)

# Fallback chains — if primary fails, try next in list
FALLBACK_CHAINS = {
    "best":       ["best",       "reasoning", "balanced"],
    "reasoning":  ["reasoning",  "balanced",  "fast"],
    "balanced":   ["balanced",   "fast"],
    "structured": ["structured", "balanced",  "fast"],
    "long_ctx":   ["long_ctx",   "balanced"],
    "fast":       ["fast",       "balanced"],
}

def get_llm_with_fallback(state: AgentState):
    """
    Returns a working LLM instance.
    Tries the primary route first, falls back down the chain on error.
    """
    primary_key = route_by_task(state)
    chain = FALLBACK_CHAINS.get(primary_key, ["balanced"])

    for key in chain:
        try:
            llm = LLM_POOL[key]
            # Lightweight health check
            llm.invoke("ping")
            return llm
        except Exception as e:
            logger.warning(f"LLM '{key}' failed: {e}. Trying next in chain.")
            continue

    # Last resort — always return balanced even without health check
    logger.error("All LLMs in fallback chain failed. Using balanced as last resort.")
    return LLM_POOL["balanced"]
```

---

## 9. tools/

### tools/tavily_tool.py

```python
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv
import os

load_dotenv()

_tavily = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=False,
    tavily_api_key=os.getenv("TAVILY_API_KEY")
)

def tavily_search(query: str) -> list:
    """
    Returns list of dicts:
    { title, url, content, source, score }
    Returns empty list on error.
    """
    try:
        results = _tavily.invoke(query)
        return [
            {
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "content": r.get("content", ""),
                "source":  "tavily",
                "published": ""
            }
            for r in results
        ]
    except Exception as e:
        print(f"[Tavily] Error: {e}")
        return []
```

### tools/wiki_tool.py

```python
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

_wiki = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(
        top_k_results=2,
        doc_content_chars_max=3000,
        lang="en"
    )
)

def wiki_search(query: str) -> dict:
    """
    Returns dict: { summary, content }
    Returns empty dict on error.
    """
    try:
        result = _wiki.invoke(query)
        return {
            "title":   query,
            "url":     f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
            "content": result,
            "source":  "wikipedia",
            "published": ""
        }
    except Exception as e:
        print(f"[Wikipedia] Error: {e}")
        return {}
```

### tools/rss_tool.py

```python
import feedparser
from datetime import datetime, timezone, timedelta

RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.reuters.com/reuters/topNews",
    "https://www.thehindu.com/feeder/default.rss",
    "https://indianexpress.com/feed/",
]

def rss_fetch(topic: str, hours_back: int = 24) -> list:
    """
    Fetches articles from all RSS feeds published in the last `hours_back` hours.
    Filters by topic keyword.
    Returns list of dicts: { title, url, content, source, published }
    """
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                # Parse published date
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                # Skip if too old
                if published and published < cutoff:
                    continue

                # Filter by topic keyword
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                if topic.lower() not in text:
                    continue

                articles.append({
                    "title":     entry.get("title", ""),
                    "url":       entry.get("link", ""),
                    "content":   entry.get("summary", ""),
                    "source":    "rss",
                    "published": str(published) if published else ""
                })
        except Exception as e:
            print(f"[RSS] Feed error {feed_url}: {e}")
            continue

    return articles
```

### tools/ddg_tool.py

```python
from langchain_community.tools import DuckDuckGoSearchRun

_ddg = DuckDuckGoSearchRun()

def ddg_search(query: str) -> list:
    """
    Returns list with one dict containing DuckDuckGo results.
    Returns empty list on error.
    """
    try:
        result = _ddg.invoke(query)
        return [{
            "title":     f"DuckDuckGo results for: {query}",
            "url":       "",
            "content":   result,
            "source":    "duckduckgo",
            "published": ""
        }]
    except Exception as e:
        print(f"[DuckDuckGo] Error: {e}")
        return []
```

---

## 10. rag/chunking_strategy.py

```python
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    SentenceTransformersTokenTextSplitter
)

# For: topic PDFs, news articles, Wikipedia content
# Larger chunks so facts have surrounding context
knowledge_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " "],
    length_function=len,
    is_separator_regex=False
)

# For: your past speeches, debate scripts, personal notes
# Medium chunks so each chunk = one complete argument point
style_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=80,
    separators=["\n\n", "\n", ". ", "! ", "? "],
    length_function=len,
    is_separator_regex=False
)

# For: debate theory books, rhetoric guides, argument pattern docs
# Token-aware so embeddings are never truncated
reasoning_splitter = SentenceTransformersTokenTextSplitter(
    chunk_overlap=30,
    tokens_per_chunk=180,
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# For: YouTube transcripts (no punctuation structure)
# Smaller chunks, word-boundary split only
youtube_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=60,
    separators=[" ", ""],
    length_function=len,
    is_separator_regex=False
)

# Map doc_type string to the correct splitter
SPLITTER_MAP = {
    "topic_pdf":      knowledge_splitter,
    "news":           knowledge_splitter,
    "wikipedia":      knowledge_splitter,
    "your_speech":    style_splitter,
    "debate_format":  style_splitter,
    "personal_notes": style_splitter,
    "debate_theory":  reasoning_splitter,
    "rhetoric":       reasoning_splitter,
    "argument_theory":reasoning_splitter,
    "youtube_debate": youtube_splitter,
    "youtube_ted":    youtube_splitter,
}

def get_splitter(doc_type: str):
    return SPLITTER_MAP.get(doc_type, knowledge_splitter)
```

---

## 11. rag/embeddings.py

```python
from langchain_community.embeddings import HuggingFaceEmbeddings

# For knowledge_db: best quality for factual retrieval
# Size on disk: ~420 MB
quality_embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# For style_db: fast, good quality for short style chunks
# Size on disk: ~80 MB
fast_embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# For reasoning_db: optimised for question-to-answer retrieval
# Size on disk: ~420 MB
qa_embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/multi-qa-mpnet-base-dot-v1",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# Which embedding model goes with which DB
DB_EMBEDDING_MAP = {
    "knowledge_db":  quality_embeddings,
    "style_db":      fast_embeddings,
    "reasoning_db":  qa_embeddings,
}
```

---

## 12. rag/ingest.py

Run this once to build the knowledge base. Re-run whenever you add new PDFs, websites, or YouTube videos.

```python
import fitz  # PyMuPDF
from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
import requests
import json
from langchain_community.vectorstores import Chroma
from rag.chunking_strategy import get_splitter
from rag.embeddings import DB_EMBEDDING_MAP

CHROMA_PATHS = {
    "knowledge_db":  "./chroma/knowledge_db",
    "style_db":      "./chroma/style_db",
    "reasoning_db":  "./chroma/reasoning_db",
}

# Which doc_type goes into which DB
DOC_TYPE_TO_DB = {
    "topic_pdf":       "knowledge_db",
    "news":            "knowledge_db",
    "wikipedia":       "knowledge_db",
    "your_speech":     "style_db",
    "debate_format":   "style_db",
    "personal_notes":  "style_db",
    "debate_theory":   "reasoning_db",
    "rhetoric":        "reasoning_db",
    "argument_theory": "reasoning_db",
    "youtube_debate":  "reasoning_db",
    "youtube_ted":     "reasoning_db",
}

def ingest_pdf(pdf_path: str, doc_type: str) -> list:
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    splitter = get_splitter(doc_type)
    chunks = splitter.split_text(text)
    return [
        {"text": chunk, "source": pdf_path, "type": doc_type}
        for chunk in chunks
    ]

def ingest_youtube(video_id: str, doc_type: str) -> list:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([t["text"] for t in transcript])
        splitter = get_splitter(doc_type)
        chunks = splitter.split_text(full_text)
        return [
            {"text": chunk, "source": f"youtube:{video_id}", "type": doc_type}
            for chunk in chunks
        ]
    except Exception as e:
        print(f"[Ingest] YouTube error {video_id}: {e}")
        return []

def ingest_website(url: str, doc_type: str) -> list:
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        splitter = get_splitter(doc_type)
        chunks = splitter.split_text(text)
        return [
            {"text": chunk, "source": url, "type": doc_type}
            for chunk in chunks
        ]
    except Exception as e:
        print(f"[Ingest] Website error {url}: {e}")
        return []

def build_knowledge_base(all_documents: list):
    """
    Routes each document to the correct ChromaDB store based on doc_type.
    Creates or updates the store.
    """
    # Group documents by target DB
    db_docs = {"knowledge_db": [], "style_db": [], "reasoning_db": []}

    for doc in all_documents:
        target_db = DOC_TYPE_TO_DB.get(doc["type"], "knowledge_db")
        db_docs[target_db].append(doc)

    # Build each store
    for db_name, docs in db_docs.items():
        if not docs:
            print(f"[Ingest] No documents for {db_name}, skipping.")
            continue

        texts = [d["text"] for d in docs]
        metadatas = [{"source": d["source"], "type": d["type"]} for d in docs]
        embedding = DB_EMBEDDING_MAP[db_name]
        path = CHROMA_PATHS[db_name]

        Chroma.from_texts(
            texts=texts,
            embedding=embedding,
            metadatas=metadatas,
            persist_directory=path
        )
        print(f"[Ingest] Built {db_name} with {len(docs)} chunks at {path}")

def run_ingest():
    with open("rag/sources.json", "r") as f:
        sources = json.load(f)

    all_docs = []

    for item in sources.get("pdfs", []):
        print(f"[Ingest] PDF: {item['path']}")
        all_docs.extend(ingest_pdf(item["path"], item["type"]))

    for item in sources.get("youtube", []):
        print(f"[Ingest] YouTube: {item['video_id']}")
        all_docs.extend(ingest_youtube(item["video_id"], item["type"]))

    for item in sources.get("websites", []):
        print(f"[Ingest] Website: {item['url']}")
        all_docs.extend(ingest_website(item["url"], item["type"]))

    print(f"[Ingest] Total chunks to index: {len(all_docs)}")
    build_knowledge_base(all_docs)
    print("[Ingest] Done.")

if __name__ == "__main__":
    run_ingest()
```

---

## 13. rag/sources.json

Add every PDF, website, and YouTube video you want in the knowledge base here. Run `ingest.py` after updating.

```json
{
  "pdfs": [
    {
      "path": "knowledge_base/pdfs/debate_frameworks/british_parliamentary.pdf",
      "type": "debate_format"
    },
    {
      "path": "knowledge_base/pdfs/argument_theory/rhetoric_aristotle.pdf",
      "type": "rhetoric"
    },
    {
      "path": "knowledge_base/pdfs/your_past_speeches/my_speech_feminism.pdf",
      "type": "your_speech"
    },
    {
      "path": "knowledge_base/pdfs/topic_pdfs/feminism_overview.pdf",
      "type": "topic_pdf"
    }
  ],
  "youtube": [
    {
      "video_id": "VIDEO_ID_HERE",
      "type": "youtube_debate",
      "description": "Oxford Union debate on feminism"
    },
    {
      "video_id": "VIDEO_ID_HERE",
      "type": "youtube_ted",
      "description": "TED talk on geopolitics"
    }
  ],
  "websites": [
    {
      "url": "https://idebate.org/debatabase",
      "type": "debate_theory"
    },
    {
      "url": "https://debate.org",
      "type": "debate_theory"
    }
  ]
}
```

To get a YouTube video_id: from `youtube.com/watch?v=ABC123XYZ` the video_id is `ABC123XYZ`.

---

## 14. rag/retrieval_pipeline.py

```python
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from rag.embeddings import DB_EMBEDDING_MAP

CHROMA_PATHS = {
    "knowledge_db": "./chroma/knowledge_db",
    "style_db":     "./chroma/style_db",
    "reasoning_db": "./chroma/reasoning_db",
}

# Retrieval config per node
# ratio is informational; k is what actually controls how many chunks
RETRIEVAL_CONFIG = {
    "rag_enrich_node": {
        "knowledge": {"k": 6},
        "reasoning": {"k": 4},
        "style":     {"k": 0},
    },
    "argue_node": {
        "knowledge": {"k": 3},
        "reasoning": {"k": 5},
        "style":     {"k": 2},
    },
    "coach_node": {
        "knowledge": {"k": 2},
        "reasoning": {"k": 3},
        "style":     {"k": 5},
    },
}

def _load_db(db_name: str) -> Chroma:
    return Chroma(
        persist_directory=CHROMA_PATHS[db_name],
        embedding_function=DB_EMBEDDING_MAP[db_name]
    )

def _build_hybrid_retriever(db_name: str, k: int) -> EnsembleRetriever:
    """BM25 40% + Vector 60% for knowledge_db"""
    db = _load_db(db_name)
    all_docs = db.get()
    texts = all_docs["documents"]
    metadatas = all_docs["metadatas"]

    bm25 = BM25Retriever.from_texts(texts, metadatas=metadatas)
    bm25.k = k

    vector = db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )

    return EnsembleRetriever(
        retrievers=[bm25, vector],
        weights=[0.4, 0.6]
    )

def _build_semantic_retriever(db_name: str, k: int):
    """Pure cosine similarity for style_db"""
    db = _load_db(db_name)
    return db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k, "score_threshold": 0.72}
    )

def _build_mmr_retriever(db_name: str, k: int):
    """MMR for reasoning_db — diverse results"""
    db = _load_db(db_name)
    return db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": 25,
            "lambda_mult": 0.65
        }
    )

def retrieve_for_node(node_name: str, query: str) -> dict:
    """
    Main retrieval function. Call this from any agent node.
    Returns dict with keys: knowledge, reasoning, style (whichever are active).
    """
    config = RETRIEVAL_CONFIG.get(node_name, RETRIEVAL_CONFIG["rag_enrich_node"])
    results = {}

    if config["knowledge"]["k"] > 0:
        try:
            retriever = _build_hybrid_retriever("knowledge_db", config["knowledge"]["k"])
            results["knowledge"] = retriever.invoke(query)
        except Exception as e:
            print(f"[RAG] knowledge_db retrieval error: {e}")
            results["knowledge"] = []

    if config["reasoning"]["k"] > 0:
        try:
            retriever = _build_mmr_retriever("reasoning_db", config["reasoning"]["k"])
            results["reasoning"] = retriever.invoke(query)
        except Exception as e:
            print(f"[RAG] reasoning_db retrieval error: {e}")
            results["reasoning"] = []

    if config["style"]["k"] > 0:
        try:
            retriever = _build_semantic_retriever("style_db", config["style"]["k"])
            results["style"] = retriever.invoke(query)
        except Exception as e:
            print(f"[RAG] style_db retrieval error: {e}")
            results["style"] = []

    return results

def format_retrieved_context(chunks: dict) -> str:
    """Formats retrieved chunks into a labelled string for LLM prompts."""
    context = ""

    if chunks.get("knowledge"):
        context += "DOMAIN KNOWLEDGE:\n"
        context += "\n---\n".join([c.page_content for c in chunks["knowledge"]])
        context += "\n\n"

    if chunks.get("reasoning"):
        context += "DEBATE THEORY AND REASONING:\n"
        context += "\n---\n".join([c.page_content for c in chunks["reasoning"]])
        context += "\n\n"

    if chunks.get("style"):
        context += "YOUR DEBATE STYLE:\n"
        context += "\n---\n".join([c.page_content for c in chunks["style"]])
        context += "\n\n"

    return context.strip()
```

---

## 15. agents/ — Daily Pipeline

### agents/research_node.py

```python
from core.state import AgentState
from tools.tavily_tool import tavily_search
from tools.wiki_tool import wiki_search
from tools.rss_tool import rss_fetch
from tools.ddg_tool import ddg_search

def research_node(state: AgentState) -> AgentState:
    topic = state["topic"]
    print(f"[Research] Fetching for topic: {topic}")

    raw_articles = []

    # RSS — last 24 hours only
    rss_results = rss_fetch(topic, hours_back=24)
    raw_articles.extend(rss_results)
    print(f"[Research] RSS: {len(rss_results)} articles")

    # Tavily — deep search
    tavily_results = tavily_search(f"{topic} debate arguments 2024")
    raw_articles.extend(tavily_results)
    print(f"[Research] Tavily: {len(tavily_results)} articles")

    # Wikipedia — background
    wiki_result = wiki_search(topic)
    if wiki_result:
        raw_articles.append(wiki_result)
    print(f"[Research] Wikipedia: {'1 article' if wiki_result else 'no result'}")

    # DuckDuckGo — backup/extra
    ddg_results = ddg_search(f"{topic} current debate")
    raw_articles.extend(ddg_results)
    print(f"[Research] DuckDuckGo: {len(ddg_results)} results")

    # Calculate max article length for router
    max_len = max((len(a.get("content", "")) for a in raw_articles), default=0)

    state["raw_articles"] = raw_articles
    state["article_length"] = max_len
    return state
```

### agents/rag_enrich_node.py

```python
from core.state import AgentState
from rag.retrieval_pipeline import retrieve_for_node, format_retrieved_context

def rag_enrich_node(state: AgentState) -> AgentState:
    topic = state["topic"]
    print(f"[RAG Enrich] Retrieving context for: {topic}")

    chunks = retrieve_for_node("rag_enrich_node", topic)
    context = format_retrieved_context(chunks)

    state["enriched_context"] = context
    return state
```

### agents/filter_node.py

```python
from core.state import AgentState
from core.fallback import get_llm_with_fallback
import json

def filter_node(state: AgentState) -> AgentState:
    state["task_type"] = "filter"
    llm = get_llm_with_fallback(state)

    articles = state["raw_articles"]
    if not articles:
        state["raw_articles"] = []
        return state

    # Prepare compact article list for LLM
    article_list = [
        {"index": i, "title": a.get("title",""), "source": a.get("source",""), "url": a.get("url","")}
        for i, a in enumerate(articles)
    ]

    prompt = f"""You are a debate research assistant.
Below is a list of articles collected about the topic: {state["topic"]}

{json.dumps(article_list, indent=2)}

Return ONLY a JSON array of index numbers to KEEP.
Remove: duplicates, articles not related to the topic, articles with no useful content.
Keep: diverse sources, different perspectives, factual content.

Respond with only a JSON array like: [0, 2, 4, 5]
No explanation. No other text."""

    try:
        response = llm.invoke(prompt)
        text = response.content.strip()
        # Clean up common LLM formatting issues
        text = text.replace("```json", "").replace("```", "").strip()
        indices = json.loads(text)
        filtered = [articles[i] for i in indices if i < len(articles)]
        state["raw_articles"] = filtered
        print(f"[Filter] Kept {len(filtered)} of {len(articles)} articles")
    except Exception as e:
        print(f"[Filter] Error parsing LLM response: {e}. Keeping all articles.")
        state["raw_articles"] = articles

    return state
```

### agents/rank_node.py

```python
from core.state import AgentState
from core.fallback import get_llm_with_fallback
import json

def rank_node(state: AgentState) -> AgentState:
    state["task_type"] = "rank"
    llm = get_llm_with_fallback(state)

    articles = state["raw_articles"]
    if not articles:
        state["ranked_articles"] = []
        return state

    article_list = [
        {"index": i, "title": a.get("title",""), "source": a.get("source","")}
        for i, a in enumerate(articles)
    ]

    prompt = f"""You are ranking articles for a debate student researching: {state["topic"]}

Articles:
{json.dumps(article_list, indent=2)}

Score each article 1-10 on:
- Relevance to topic (most important)
- Source credibility
- Usefulness for debate arguments

Return ONLY a JSON array of the top 7 index numbers, ordered best first.
Like: [3, 0, 7, 1, 5, 2, 6]
No explanation. No other text."""

    try:
        response = llm.invoke(prompt)
        text = response.content.strip().replace("```json","").replace("```","").strip()
        indices = json.loads(text)[:7]
        ranked = [articles[i] for i in indices if i < len(articles)]
        state["ranked_articles"] = ranked
        print(f"[Rank] Selected top {len(ranked)} articles")
    except Exception as e:
        print(f"[Rank] Error: {e}. Using first 7 articles.")
        state["ranked_articles"] = articles[:7]

    return state
```

### agents/summarize_node.py

```python
from core.state import AgentState
from core.fallback import get_llm_with_fallback
from memory.weekly_store import save_daily_digest
from datetime import date

def summarize_node(state: AgentState) -> AgentState:
    state["task_type"] = "summarize"
    llm = get_llm_with_fallback(state)

    topic = state["topic"]
    articles = state["ranked_articles"]
    enriched = state.get("enriched_context", "")

    summaries = []
    all_key_facts = []
    all_concepts = []

    for i, article in enumerate(articles):
        prompt = f"""You are summarizing an article for a debate student. Topic: {topic}

Article Title: {article.get('title','')}
Article Content: {article.get('content','')}

Additional Context from Knowledge Base:
{enriched if i == 0 else ''}

Write in simple language a non-debate expert can understand.

Return EXACTLY in this format:
SUMMARY:
- [point 1]
- [point 2]
- [point 3]

KEY FACT: [one specific fact or statistic from this article]
CONCEPT: [one key concept or term from this article]"""

        try:
            response = llm.invoke(prompt)
            text = response.content.strip()
            summaries.append(text)

            # Extract key fact and concept for memory
            if "KEY FACT:" in text:
                fact = text.split("KEY FACT:")[1].split("\n")[0].strip()
                all_key_facts.append(fact)
            if "CONCEPT:" in text:
                concept = text.split("CONCEPT:")[1].split("\n")[0].strip()
                all_concepts.append(concept)
        except Exception as e:
            print(f"[Summarize] Error on article {i}: {e}")
            summaries.append(f"- {article.get('title','')}: Content unavailable.")

    state["summaries"] = summaries
    state["key_facts"] = all_key_facts
    state["concepts"] = all_concepts

    # Save to memory immediately after summarizing
    save_daily_digest(topic, {
        "summaries": "\n\n".join(summaries),
        "key_facts": all_key_facts,
        "concepts": all_concepts,
        "arguments": {},
        "debate_angle": ""
    })

    return state
```

### agents/argue_node.py

```python
from core.state import AgentState
from core.fallback import get_llm_with_fallback
from rag.retrieval_pipeline import retrieve_for_node, format_retrieved_context

def argue_node(state: AgentState) -> AgentState:
    state["task_type"] = "argue"
    llm = get_llm_with_fallback(state)

    topic = state["topic"]
    summaries = "\n\n".join(state.get("summaries", []))

    # RAG retrieval for argue node
    chunks = retrieve_for_node("argue_node", topic)
    rag_context = format_retrieved_context(chunks)

    prompt = f"""You are a debate coach building arguments.
Topic: {topic}

Research summaries:
{summaries}

Debate theory and reasoning context:
{rag_context}

Generate the following. Use debate-ready language.
Be specific. Use facts from the research where possible.

FOR ARGUMENTS (3 strong arguments supporting the topic):
FOR1: [argument]
FOR2: [argument]
FOR3: [argument]

AGAINST ARGUMENTS (3 strong arguments opposing the topic):
AGAINST1: [argument]
AGAINST2: [argument]
AGAINST3: [argument]

MIDDLE GROUND:
MIDDLE: [one nuanced position that acknowledges both sides]"""

    try:
        response = llm.invoke(prompt)
        text = response.content.strip()

        def extract(prefix, text):
            results = []
            for i in range(1, 4):
                key = f"{prefix}{i}:"
                if key in text:
                    val = text.split(key)[1].split("\n")[0].strip()
                    results.append(val)
            return results

        arguments = {
            "for":     extract("FOR", text),
            "against": extract("AGAINST", text),
            "middle":  text.split("MIDDLE:")[1].split("\n")[0].strip() if "MIDDLE:" in text else ""
        }

        state["arguments"] = arguments
    except Exception as e:
        print(f"[Argue] Error: {e}")
        state["arguments"] = {"for": [], "against": [], "middle": ""}

    return state
```

### agents/coach_node.py

```python
from core.state import AgentState
from core.fallback import get_llm_with_fallback
from rag.retrieval_pipeline import retrieve_for_node, format_retrieved_context

def coach_node(state: AgentState) -> AgentState:
    state["task_type"] = "debate"
    llm = get_llm_with_fallback(state)

    topic = state["topic"]
    summaries = "\n\n".join(state.get("summaries", []))
    arguments = state.get("arguments", {})

    # RAG — style_db at 50% weight
    chunks = retrieve_for_node("coach_node", topic)
    rag_context = format_retrieved_context(chunks)

    prompt = f"""You are a personal debate coach. You know this student's exact debate style.

STUDENT'S DEBATE STYLE (from their past speeches and notes):
{rag_context}

TOPIC: {topic}

RESEARCH SUMMARIES:
{summaries}

ARGUMENTS GENERATED:
FOR: {arguments.get('for', [])}
AGAINST: {arguments.get('against', [])}
MIDDLE: {arguments.get('middle', '')}

Now give the student exactly this, in their style:

UNIQUE ANGLE:
[An argument most debaters won't think of. Be specific.]

OPEN WITH THIS:
[A killer opening line. Match their debate format and tone.]

BUILD YOUR CASE:
CLAIM: [the main claim]
WARRANT: [why it is true, with evidence]
IMPACT: [why it matters in the real world]

TOP 3 REBUTTALS TO PREPARE FOR:
REBUTTAL1: [what opponent will say] | COUNTER: [how to respond]
REBUTTAL2: [what opponent will say] | COUNTER: [how to respond]
REBUTTAL3: [what opponent will say] | COUNTER: [how to respond]

POWER PHRASES (use these verbatim in debate):
PHRASE1: [sentence]
PHRASE2: [sentence]
PHRASE3: [sentence]
PHRASE4: [sentence]
PHRASE5: [sentence]"""

    try:
        response = llm.invoke(prompt)
        state["debate_angle"] = response.content.strip()
    except Exception as e:
        print(f"[Coach] Error: {e}")
        state["debate_angle"] = "Coach output unavailable."

    return state
```

### agents/format_node.py

```python
from core.state import AgentState
from core.fallback import get_llm_with_fallback
from memory.weekly_store import update_debate_angle
from datetime import date

def format_node(state: AgentState) -> AgentState:
    state["task_type"] = "format"

    topic = state["topic"].upper()
    summaries = state.get("summaries", [])
    arguments = state.get("arguments", {})
    debate_angle = state.get("debate_angle", "")
    key_facts = state.get("key_facts", [])

    # Build message without markdown — WhatsApp safe
    lines = []
    lines.append(f"{'='*30}")
    lines.append(f"TOPIC: {topic}")
    lines.append(f"{'='*30}")
    lines.append("")

    lines.append("BACKGROUND")
    lines.append("-"*20)
    if summaries:
        lines.append(summaries[0])
    lines.append("")

    lines.append("WHATS HAPPENING NOW")
    lines.append("-"*20)
    for s in summaries[1:4]:
        lines.append(s)
    lines.append("")

    lines.append("KEY FACTS TO USE")
    lines.append("-"*20)
    for f in key_facts[:3]:
        lines.append(f"• {f}")
    lines.append("")

    lines.append("ARGUMENTS FOR")
    lines.append("-"*20)
    for arg in arguments.get("for", []):
        lines.append(f"• {arg}")
    lines.append("")

    lines.append("ARGUMENTS AGAINST")
    lines.append("-"*20)
    for arg in arguments.get("against", []):
        lines.append(f"• {arg}")
    lines.append("")

    lines.append("MIDDLE GROUND")
    lines.append("-"*20)
    lines.append(arguments.get("middle", ""))
    lines.append("")

    lines.append("="*30)
    lines.append("YOUR DEBATE COACH")
    lines.append("="*30)
    lines.append(debate_angle)
    lines.append("")
    lines.append("="*30)

    state["final_doc"] = "\n".join(lines)

    # Update memory with debate angle
    update_debate_angle(state["topic"], debate_angle)

    return state
```

---

## 16. agents/ — Night Agent

### agents/night_agent.py

```python
from core.state import AgentState
from core.fallback import get_llm_with_fallback
from memory.weekly_store import get_today_log, mark_as_studied
from delivery.whatsapp import send_message, wait_for_reply
from datetime import date
import json

YES_WORDS = {"yes", "y", "yep", "yeah", "yup", "done", "read", "studied", "haan", "ha"}
NO_WORDS  = {"no", "n", "nope", "nah", "didn't", "didnt", "nahi", "na", "skip"}

def night_agent_node(state: AgentState) -> AgentState:
    send_message(
        "Hey! Quick check-in.\n\n"
        "Did you read today's debate digest?\n"
        "Reply: yes or no"
    )

    reply = wait_for_reply(timeout_minutes=30)

    if reply.lower() in YES_WORDS or any(w in reply.lower() for w in YES_WORDS):
        return quiz_mode(state)
    else:
        return bedtime_mode(state)


def quiz_mode(state: AgentState) -> AgentState:
    state["task_type"] = "quiz"
    llm = get_llm_with_fallback(state)

    today_entries = get_today_log()
    if not today_entries:
        send_message("No digest found for today. Get some rest!")
        return state

    # Combine all today's content
    combined = "\n\n".join([
        f"Topic: {e['topic']}\n{e['summaries']}\n{e.get('debate_angle','')}"
        for e in today_entries
    ])

    prompt = f"""Create a 5-question quiz from this debate content.
Mix: 2 factual questions, 2 argument-based questions, 1 application question.

Content:
{combined}

Return ONLY valid JSON in exactly this format:
{{
  "questions": [
    {{
      "q": "Question text",
      "a": "Option A text",
      "b": "Option B text",
      "c": "Option C text",
      "d": "Option D text",
      "answer": "a"
    }}
  ]
}}

Keep language simple. Make questions test real understanding, not trivia."""

    try:
        response = llm.invoke(prompt)
        text = response.content.strip().replace("```json","").replace("```","").strip()
        quiz_data = json.loads(text)
        questions = quiz_data["questions"][:5]
    except Exception as e:
        print(f"[Quiz] Parse error: {e}")
        send_message("Could not generate quiz tonight. Study well and try tomorrow!")
        mark_as_studied(str(date.today()), True, score=None)
        return state

    # Format and send questions
    msg = "QUICK REVISION QUIZ\n" + "-"*20 + "\n\n"
    for i, q in enumerate(questions, 1):
        msg += f"Q{i}: {q['q']}\n"
        msg += f"A) {q['a']}\n"
        msg += f"B) {q['b']}\n"
        msg += f"C) {q['c']}\n"
        msg += f"D) {q['d']}\n\n"
    msg += "Reply with your answers like: 1a 2b 3c 4d 5a"

    send_message(msg)

    # Wait for answers
    answers_reply = wait_for_reply(timeout_minutes=10)

    # Score
    correct = 0
    feedback_lines = []
    user_answers = answers_reply.lower().replace(" ", "")

    for i, q in enumerate(questions, 1):
        # Try to extract answer for question i
        user_ans = ""
        for char in user_answers:
            if str(i) in user_answers:
                idx = user_answers.find(str(i))
                if idx + 1 < len(user_answers):
                    user_ans = user_answers[idx + 1]
                break

        correct_ans = q["answer"].lower()
        is_correct = user_ans == correct_ans
        if is_correct:
            correct += 1
        feedback_lines.append(
            f"Q{i}: {'Correct!' if is_correct else f'Wrong. Answer was {correct_ans.upper()}'}"
        )

    score_pct = int((correct / len(questions)) * 100)
    mark_as_studied(str(date.today()), True, score=score_pct)

    result_msg = f"RESULTS\n" + "-"*10 + "\n"
    result_msg += f"Score: {correct}/{len(questions)} ({score_pct}%)\n\n"
    result_msg += "\n".join(feedback_lines)
    result_msg += "\n\n"
    result_msg += "Excellent! You are debate-ready!" if score_pct >= 80 else "Review the weak areas tomorrow morning."

    send_message(result_msg)
    return state


def bedtime_mode(state: AgentState) -> AgentState:
    state["task_type"] = "bedtime"
    llm = get_llm_with_fallback(state)

    today_entries = get_today_log()
    if not today_entries:
        send_message("No digest found for today. Sleep well!")
        return state

    combined = "\n\n".join([
        f"Topic: {e['topic']}\n{e['summaries']}"
        for e in today_entries
    ])

    prompt = f"""The student did NOT read today's digest. They are in bed.
Give them a max 100 word version. Casual, friendly, like a friend texting.

From this content:
{combined}

Include ONLY:
1. The single most important fact (1 sentence)
2. One argument FOR (1 sentence)
3. One argument AGAINST (1 sentence)
4. One killer debate line they can use (1 sentence)

Max 100 words. No bullet symbols. Use emojis instead. No jargon."""

    try:
        response = llm.invoke(prompt)
        bedtime_msg = f"No worries! Here is the 2-min version:\n\n{response.content.strip()}\n\nSleep well!"
    except Exception as e:
        print(f"[Bedtime] Error: {e}")
        bedtime_msg = "Could not compress digest tonight. Read it in the morning!"

    send_message(bedtime_msg)
    mark_as_studied(str(date.today()), False, score=None)
    return state
```

---

## 17. agents/ — Weekend Agent

### agents/weekend_agent.py

```python
from core.state import AgentState
from core.fallback import get_llm_with_fallback
from memory.weekly_store import get_week_log
from delivery.whatsapp import send_message
import json

def weekend_agent_node(state: AgentState) -> AgentState:
    state["task_type"] = "weekend"
    llm = get_llm_with_fallback(state)

    week_log = get_week_log()
    if not week_log:
        send_message("No data from this week yet. Start reading daily digests!")
        return state

    # Calculate stats
    all_entries = [entry for day in week_log.values() for entry in day]
    days_studied = sum(1 for e in all_entries if e.get("studied"))
    scores = [e["quiz_score"] for e in all_entries if e.get("quiz_score") is not None]
    avg_score = int(sum(scores) / len(scores)) if scores else 0

    # Build week content summary for LLM
    week_content = json.dumps(week_log, indent=2)

    prompt = f"""You are filtering a week of debate research for a student.
Your job is to be RUTHLESS. Only keep what is worth memorizing long-term.

WEEK'S CONTENT:
{week_content}

REMOVE everything that is:
- A news story tied to a specific date or event
- Something that will be outdated in 6 months
- A narrative or anecdote without transferable insight
- Something answerable by a 5-second Google search

KEEP ONLY:
- Named concepts (intersectionality, comparative advantage)
- Thinking frameworks (how to evaluate a policy claim)
- Historical context that keeps repeating in debates
- Statistical facts worth memorizing for years
- Argument patterns with names (slippery slope, whataboutism)
- Philosophical positions and what they claim

Return ONLY valid JSON in exactly this format:
{{
  "concepts": [
    {{
      "title": "concept name",
      "what_it_is": "one sentence definition in simple language",
      "why_it_matters_in_debate": "one sentence",
      "remember_this": "the single most important thing to memorize",
      "source_topic": "which topic this came from"
    }}
  ],
  "frameworks": [
    {{
      "title": "framework name",
      "what_it_is": "one sentence",
      "why_it_matters_in_debate": "one sentence",
      "remember_this": "key insight",
      "source_topic": "which topic"
    }}
  ],
  "key_stats": [
    {{
      "stat": "the number or fact",
      "context": "what it means",
      "use_in_debate": "when to use this"
    }}
  ],
  "argument_patterns": [
    {{
      "pattern_name": "name of the pattern",
      "how_it_works": "one sentence",
      "example": "example from this week's topics"
    }}
  ]
}}"""

    try:
        response = llm.invoke(prompt)
        text = response.content.strip().replace("```json","").replace("```","").strip()
        knowledge = json.loads(text)
    except Exception as e:
        print(f"[Weekend] Parse error: {e}")
        send_message("Could not generate brain upload this week. Try again next Sunday.")
        return state

    # Format the brain upload message
    msg = "WEEKLY BRAIN UPLOAD\n"
    msg += "="*25 + "\n"
    msg += f"This week: {days_studied}/5 days studied\n"
    msg += f"Avg quiz score: {avg_score}%\n"
    msg += "="*25 + "\n\n"

    if knowledge.get("concepts"):
        msg += "CONCEPTS TO OWN\n\n"
        for c in knowledge["concepts"]:
            msg += f"{c['title'].upper()}\n"
            msg += f"What: {c['what_it_is']}\n"
            msg += f"In debate: {c['why_it_matters_in_debate']}\n"
            msg += f"Remember: {c['remember_this']}\n\n"

    if knowledge.get("frameworks"):
        msg += "THINKING FRAMEWORKS\n\n"
        for f in knowledge["frameworks"]:
            msg += f"{f['title'].upper()}\n"
            msg += f"What: {f['what_it_is']}\n"
            msg += f"Use when: {f['why_it_matters_in_debate']}\n\n"

    if knowledge.get("key_stats"):
        msg += "STATS WORTH MEMORIZING\n\n"
        for s in knowledge["key_stats"]:
            msg += f"• {s['stat']}\n"
            msg += f"  Context: {s['context']}\n"
            msg += f"  Use when: {s['use_in_debate']}\n\n"

    if knowledge.get("argument_patterns"):
        msg += "ARGUMENT PATTERNS\n\n"
        for p in knowledge["argument_patterns"]:
            msg += f"{p['pattern_name']}\n"
            msg += f"How: {p['how_it_works']}\n"
            msg += f"Example: {p['example']}\n\n"

    msg += "="*25 + "\n"
    msg += "Save this. These are yours to keep."

    send_message(msg)
    return state
```

---

## 18. memory/weekly_store.py

```python
import json
from datetime import date, datetime, timedelta
from pathlib import Path

LOG_FILE = Path("memory/weekly_log.json")

def _load_log() -> dict:
    if not LOG_FILE.exists():
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.write_text("{}")
    with open(LOG_FILE, "r") as f:
        return json.load(f)

def _save_log(log: dict):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def save_daily_digest(topic: str, content: dict):
    log = _load_log()
    today = str(date.today())
    if today not in log:
        log[today] = []

    log[today].append({
        "topic":        topic,
        "summaries":    content.get("summaries", ""),
        "arguments":    content.get("arguments", {}),
        "key_facts":    content.get("key_facts", []),
        "concepts":     content.get("concepts", []),
        "debate_angle": content.get("debate_angle", ""),
        "studied":      False,
        "quiz_score":   None,
        "timestamp":    datetime.now().isoformat()
    })

    _save_log(log)

def update_debate_angle(topic: str, debate_angle: str):
    log = _load_log()
    today = str(date.today())
    if today in log:
        for entry in log[today]:
            if entry["topic"] == topic:
                entry["debate_angle"] = debate_angle
    _save_log(log)

def mark_as_studied(date_str: str, studied: bool, score: int = None):
    log = _load_log()
    if date_str in log:
        for entry in log[date_str]:
            entry["studied"] = studied
            if score is not None:
                entry["quiz_score"] = score
    _save_log(log)

def get_today_log() -> list:
    log = _load_log()
    return log.get(str(date.today()), [])

def get_week_log() -> dict:
    log = _load_log()
    result = {}
    for i in range(7):
        day = str(date.today() - timedelta(days=i))
        if day in log:
            result[day] = log[day]
    return result
```

---

## 19. delivery/whatsapp.py

```python
from twilio.rest import Client
from dotenv import load_dotenv
import os
import time

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_FROM")
TO_NUMBER   = os.getenv("YOUR_WHATSAPP_NUMBER")
DEV_MODE    = os.getenv("DEV_MODE", "false").lower() == "true"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

MAX_CHARS = 4000  # WhatsApp limit is 4096, keep buffer

def send_message(text: str):
    """Sends a WhatsApp message. Splits if over MAX_CHARS. Prints in DEV_MODE."""
    if DEV_MODE:
        print(f"\n[WhatsApp DEV]\n{text}\n{'='*40}")
        return

    # Split long messages
    if len(text) <= MAX_CHARS:
        _send_single(text)
    else:
        parts = _split_message(text)
        for part in parts:
            _send_single(part)
            time.sleep(1)  # avoid rate limiting

def _send_single(text: str):
    try:
        message = client.messages.create(
            from_=FROM_NUMBER,
            to=TO_NUMBER,
            body=text
        )
        print(f"[WhatsApp] Sent: {message.sid}")
    except Exception as e:
        print(f"[WhatsApp] Send error: {e}")
        # Retry once
        try:
            time.sleep(3)
            client.messages.create(from_=FROM_NUMBER, to=TO_NUMBER, body=text)
        except Exception as e2:
            print(f"[WhatsApp] Retry failed: {e2}")

def _split_message(text: str) -> list:
    parts = []
    while len(text) > MAX_CHARS:
        # Split at last newline before limit
        split_at = text.rfind("\n", 0, MAX_CHARS)
        if split_at == -1:
            split_at = MAX_CHARS
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        parts.append(text)
    return parts

def wait_for_reply(timeout_minutes: int = 30) -> str:
    """
    Polls Twilio for an incoming WhatsApp message.
    Returns message body string or 'no' on timeout.
    """
    if DEV_MODE:
        return input("[WhatsApp DEV] Simulate reply: ").strip()

    deadline = time.time() + (timeout_minutes * 60)
    last_check_sid = None

    while time.time() < deadline:
        try:
            messages = client.messages.list(
                to=FROM_NUMBER,
                from_=TO_NUMBER,
                limit=1
            )
            if messages:
                msg = messages[0]
                if msg.sid != last_check_sid:
                    last_check_sid = msg.sid
                    return msg.body.strip()
        except Exception as e:
            print(f"[WhatsApp] Poll error: {e}")

        time.sleep(30)  # poll every 30 seconds

    print("[WhatsApp] Reply timeout.")
    return "no"
```

---

## 20. graph.py

```python
from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.research_node   import research_node
from agents.rag_enrich_node import rag_enrich_node
from agents.filter_node     import filter_node
from agents.rank_node       import rank_node
from agents.summarize_node  import summarize_node
from agents.argue_node      import argue_node
from agents.coach_node      import coach_node
from agents.format_node     import format_node
from agents.night_agent     import night_agent_node
from agents.weekend_agent   import weekend_agent_node
from delivery.whatsapp      import send_message

def build_daily_graph():
    graph = StateGraph(AgentState)

    graph.add_node("research",   research_node)
    graph.add_node("rag_enrich", rag_enrich_node)
    graph.add_node("filter",     filter_node)
    graph.add_node("rank",       rank_node)
    graph.add_node("summarize",  summarize_node)
    graph.add_node("argue",      argue_node)
    graph.add_node("coach",      coach_node)
    graph.add_node("format",     format_node)

    graph.set_entry_point("research")
    graph.add_edge("research",   "rag_enrich")
    graph.add_edge("rag_enrich", "filter")
    graph.add_edge("filter",     "rank")
    graph.add_edge("rank",       "summarize")
    graph.add_edge("summarize",  "argue")
    graph.add_edge("argue",      "coach")
    graph.add_edge("coach",      "format")
    graph.add_edge("format",     END)

    return graph.compile()

def build_night_graph():
    graph = StateGraph(AgentState)
    graph.add_node("night", night_agent_node)
    graph.set_entry_point("night")
    graph.add_edge("night", END)
    return graph.compile()

def build_weekend_graph():
    graph = StateGraph(AgentState)
    graph.add_node("weekend", weekend_agent_node)
    graph.set_entry_point("weekend")
    graph.add_edge("weekend", END)
    return graph.compile()
```

---

## 21. main.py

```python
import argparse
import json
from graph import build_daily_graph, build_night_graph, build_weekend_graph
from delivery.whatsapp import send_message
from core.state import AgentState

def run_daily(topic_override: str = None):
    with open("topics.json", "r") as f:
        topics = json.load(f)

    if topic_override:
        topics = [topic_override]

    graph = build_daily_graph()

    for topic in topics:
        print(f"\n{'='*40}")
        print(f"Processing topic: {topic}")
        print(f"{'='*40}")

        initial_state: AgentState = {
            "topic":          topic,
            "raw_articles":   [],
            "enriched_context": "",
            "ranked_articles":[],
            "summaries":      [],
            "key_facts":      [],
            "concepts":       [],
            "arguments":      {},
            "debate_angle":   "",
            "final_doc":      "",
            "task_type":      "fetch",
            "article_length": 0,
            "studied_today":  None,
            "quiz_score":     None,
        }

        result = graph.invoke(initial_state)
        send_message(result["final_doc"])
        print(f"[Main] Digest sent for: {topic}")

def run_night():
    graph = build_night_graph()
    initial_state: AgentState = {
        "topic": "", "raw_articles": [], "enriched_context": "",
        "ranked_articles": [], "summaries": [], "key_facts": [],
        "concepts": [], "arguments": {}, "debate_angle": "",
        "final_doc": "", "task_type": "quiz", "article_length": 0,
        "studied_today": None, "quiz_score": None,
    }
    graph.invoke(initial_state)

def run_weekend():
    graph = build_weekend_graph()
    initial_state: AgentState = {
        "topic": "", "raw_articles": [], "enriched_context": "",
        "ranked_articles": [], "summaries": [], "key_facts": [],
        "concepts": [], "arguments": {}, "debate_angle": "",
        "final_doc": "", "task_type": "weekend", "article_length": 0,
        "studied_today": None, "quiz_score": None,
    }
    graph.invoke(initial_state)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "night", "weekend"], required=True)
    parser.add_argument("--topic", type=str, default=None, help="Override topics.json for testing")
    args = parser.parse_args()

    if args.mode == "daily":
        run_daily(args.topic)
    elif args.mode == "night":
        run_night()
    elif args.mode == "weekend":
        run_weekend()
```

---

## 22. .github/workflows/scheduler.yml

```yaml
name: DebateIQ Scheduler

on:
  schedule:
    # Daily digest — 8:00 AM IST = 2:30 AM UTC
    - cron: '30 2 * * 1-5'
    # Night check-in — 10:30 PM IST = 5:00 PM UTC
    - cron: '0 17 * * 1-5'
    # Weekend brain upload — Sunday 9:00 AM IST = 3:30 AM UTC
    - cron: '30 3 * * 0'

  # Allow manual trigger from GitHub Actions tab
  workflow_dispatch:
    inputs:
      mode:
        description: 'Run mode'
        required: true
        default: 'daily'
        type: choice
        options: [daily, night, weekend]

jobs:
  run-agent:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Determine run mode from cron
        id: mode
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            echo "mode=${{ github.event.inputs.mode }}" >> $GITHUB_OUTPUT
          elif [ "${{ github.event.schedule }}" = "30 2 * * 1-5" ]; then
            echo "mode=daily" >> $GITHUB_OUTPUT
          elif [ "${{ github.event.schedule }}" = "0 17 * * 1-5" ]; then
            echo "mode=night" >> $GITHUB_OUTPUT
          else
            echo "mode=weekend" >> $GITHUB_OUTPUT
          fi

      - name: Run agent
        env:
          GROQ_API_KEY:          ${{ secrets.GROQ_API_KEY }}
          GOOGLE_API_KEY:        ${{ secrets.GOOGLE_API_KEY }}
          TAVILY_API_KEY:        ${{ secrets.TAVILY_API_KEY }}
          TWILIO_ACCOUNT_SID:    ${{ secrets.TWILIO_ACCOUNT_SID }}
          TWILIO_AUTH_TOKEN:     ${{ secrets.TWILIO_AUTH_TOKEN }}
          TWILIO_WHATSAPP_FROM:  ${{ secrets.TWILIO_WHATSAPP_FROM }}
          YOUR_WHATSAPP_NUMBER:  ${{ secrets.YOUR_WHATSAPP_NUMBER }}
        run: |
          python main.py --mode ${{ steps.mode.outputs.mode }}
```

Add all 7 secrets in: GitHub repo → Settings → Secrets and variables → Actions → New repository secret

---

## 23. Prompt Templates

### Filter Node Prompt
- Input: topic string, list of article dicts (index, title, source, url)
- Output: JSON array of index numbers to keep
- LLM: Llama 3.1 8B
- Temperature: 0.1

### Rank Node Prompt
- Input: topic string, list of article dicts (index, title, source)
- Output: JSON array of top 7 index numbers ordered best first
- LLM: Llama 3.1 8B
- Temperature: 0.1

### Summarize Node Prompt
- Input: topic, article title, article content, enriched_context (first article only)
- Output: SUMMARY bullets + KEY FACT + CONCEPT
- LLM: Llama 3.3 70B
- Temperature: 0.3

### Argue Node Prompt
- Input: topic, summaries, RAG context from reasoning_db and knowledge_db
- Output: FOR1/FOR2/FOR3, AGAINST1/AGAINST2/AGAINST3, MIDDLE
- LLM: DeepSeek R1
- Temperature: 0.4

### Coach Node Prompt
- Input: topic, summaries, arguments dict, RAG context (style_db at 50%)
- Output: UNIQUE ANGLE, OPEN WITH THIS, CLAIM/WARRANT/IMPACT, REBUTTAL1-3 with COUNTER, PHRASE1-5
- LLM: Gemini 1.5 Pro
- Temperature: 0.5

### Quiz Node Prompt
- Input: today's combined digest content
- Output: JSON with 5 questions, each with q/a/b/c/d/answer fields
- LLM: Mixtral 8x7B
- Temperature: 0.1

### Bedtime Node Prompt
- Input: today's combined summaries
- Output: max 100 words, 1 fact + 1 for + 1 against + 1 line, casual tone with emojis
- LLM: Llama 3.3 70B
- Temperature: 0.3

### Weekend Filter Prompt
- Input: full week_log JSON
- Output: JSON with concepts, frameworks, key_stats, argument_patterns arrays
- LLM: DeepSeek R1
- Temperature: 0.4

---

## 24. RAG Retrieval Config

```
rag_enrich_node
  knowledge_db: k=6, hybrid (BM25 40% + vector 60%)
  reasoning_db: k=4, MMR (lambda=0.65, fetch_k=25)
  style_db:     not used

argue_node
  knowledge_db: k=3, hybrid
  reasoning_db: k=5, MMR
  style_db:     k=2, semantic (threshold=0.72)

coach_node
  knowledge_db: k=2, hybrid
  reasoning_db: k=3, MMR
  style_db:     k=5, semantic (threshold=0.72)
```

---

## 25. WhatsApp Output Format

Rules for every message sent:
- No `*bold*` markdown — WhatsApp renders asterisks as bold but it looks messy in long text
- No `#` headers
- Use `=` and `-` lines as separators
- Use emoji as section markers
- Max 4000 characters per message — split at newline boundaries if longer
- One blank line between sections
- All caps for section headers

---

## 26. Error Handling Rules

Apply these in every agent and tool file without exception:

```
1. Every external API call (LLM, Tavily, Twilio, Wikipedia) in try/except
2. Every JSON parse in try/except with fallback to raw string handling
3. Tools return empty list or empty dict on error, never raise
4. Agents fall back to previous state values if a node fails
5. LLM calls always go through get_llm_with_fallback(), never direct LLM_POOL access
6. weekly_log.json always: load → modify → save. Never overwrite directly.
7. WhatsApp send retries once on failure with 3 second delay
8. RSS tool catches per-feed errors and continues to next feed
9. Ingest functions skip failed items and log the error, never crash full ingest
10. Night agent returns "no" path on reply timeout instead of crashing
```

---

## 27. Testing Checklist

Run before each sprint is marked complete.

### Sprint 0
- [ ] `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('GROQ_API_KEY')[:5])"` prints key prefix
- [ ] WhatsApp test message received on phone

### Sprint 1
- [ ] `python tests/test_router.py` — all 10 task_types route to correct LLM key
- [ ] Fallback test passes — simulated failure routes to next in chain

### Sprint 2
- [ ] `python tests/test_tools.py` — all 4 tools return results for "feminism India"
- [ ] RSS returns only last 24 hours articles
- [ ] No tool crashes when source is unavailable

### Sprint 3
- [ ] `python rag/ingest.py` runs without error
- [ ] `ls chroma/` shows knowledge_db, style_db, reasoning_db
- [ ] `retrieve_for_node("coach_node", "feminism")` returns chunks from style_db
- [ ] `retrieve_for_node("argue_node", "feminism")` returns diverse chunks from reasoning_db

### Sprint 4
- [ ] `python main.py --mode daily --topic "feminism"` runs through rank node
- [ ] `state["ranked_articles"]` contains 5-7 items
- [ ] `state["enriched_context"]` is non-empty

### Sprint 5
- [ ] Full digest received on WhatsApp
- [ ] All sections present in message
- [ ] No markdown symbols visible in WhatsApp

### Sprint 6
- [ ] `python tests/test_memory.py` passes all assertions
- [ ] After daily run, `memory/weekly_log.json` has today's entry with all fields

### Sprint 7
- [ ] Night agent check-in received on WhatsApp
- [ ] `yes` reply → 5 questions received → answers → score received
- [ ] `no` reply → bedtime summary received (count words: must be under 100)
- [ ] `weekly_log.json` updated correctly after both paths

### Sprint 8
- [ ] `python main.py --mode weekend` with 3+ days of log data
- [ ] Brain upload received on WhatsApp
- [ ] Output contains no news stories — only concepts, frameworks, stats, patterns
- [ ] Study stats are accurate

### Sprint 9
- [ ] All 3 GitHub Actions workflows trigger via manual dispatch
- [ ] All 3 WhatsApp messages received
- [ ] No unhandled exceptions in any Actions log
- [ ] Tavily failure → DuckDuckGo fallback (test by setting wrong TAVILY_API_KEY temporarily)
