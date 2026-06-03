"""File-based LLM response cache keyed by (model_name + prompt) hash.

Purpose: zero-cost insurance against the Groq 100K TPD free-tier ceiling.
The 14 priority topics rotate; a topic re-run within ~30 days reuses the
prior LLM output instead of burning fresh tokens.

Storage layout: one JSON file per cache entry under .cache/llm/<sha256>.json.
The directory is gitignored. Entries older than TTL_SECONDS are ignored on
read but only physically removed on a write to the same key.

Use `cached_invoke(llm, prompt, scope=...)` from any node. If the call hits
cache it returns a synthetic response object with `.content` set. On miss
it forwards to llm.invoke(prompt) and stores the result.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = _PROJECT_ROOT / ".cache" / "llm"
TTL_SECONDS = 30 * 24 * 3600  # 30 days


def _enabled() -> bool:
    # Respect an off switch so tests can disable caching deterministically.
    return os.getenv("DEBATEIQ_PROMPT_CACHE", "1") not in {"0", "false", "False"}


def _model_id(llm: Any) -> str:
    # Try the conventional attributes; fall back to the class name.
    for attr in ("model", "model_name", "_model", "chain"):
        value = getattr(llm, attr, None)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ",".join(str(v) for v in value)
    return llm.__class__.__name__


def _key(model: str, prompt: str, scope: str) -> Path:
    raw = f"{scope}::{model}::{prompt}".encode("utf-8", errors="replace")
    digest = hashlib.sha256(raw).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def _atomic_write(path: Path, payload: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".llm.", suffix=".json.tmp", dir=str(CACHE_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as h:
            json.dump(payload, h)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class _CachedResponse:
    __slots__ = ("content",)

    def __init__(self, content: str):
        self.content = content


def lookup(model: str, prompt: str, scope: str = "default") -> _CachedResponse | None:
    if not _enabled():
        return None
    path = _key(model, prompt, scope)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as h:
            payload = json.load(h)
    except (OSError, json.JSONDecodeError):
        return None
    if time.time() - payload.get("ts", 0) > TTL_SECONDS:
        return None
    return _CachedResponse(payload.get("content", ""))


def store(model: str, prompt: str, content: str, scope: str = "default"):
    if not _enabled() or not content:
        return
    try:
        _atomic_write(
            _key(model, prompt, scope),
            {"ts": time.time(), "model": model, "scope": scope, "content": content},
        )
    except Exception:
        pass


def cached_invoke(llm: Any, prompt: str, scope: str = "default") -> Any:
    """Cache-aware wrapper around llm.invoke(prompt).

    Returns the LLM's response object (or a _CachedResponse on hit).
    Both expose `.content`, so downstream `getattr(r, "content", r)` works.
    """
    model = _model_id(llm)
    cached = lookup(model, prompt, scope)
    if cached is not None:
        return cached

    response = llm.invoke(prompt)
    content = str(getattr(response, "content", response))
    store(model, prompt, content, scope=scope)
    return response
