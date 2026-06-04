from __future__ import annotations

import os


PROXY_ENV_KEYS = [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
]

BROKEN_PROXY_MARKERS = {
    "http://127.0.0.1:9",
    "https://127.0.0.1:9",
    "127.0.0.1:9",
    "http://localhost:9",
    "https://localhost:9",
    "localhost:9",
}


def clear_broken_local_proxies() -> list[str]:
    cleared = []
    for key in PROXY_ENV_KEYS:
        value = os.getenv(key)
        if not value:
            continue
        normalized = value.strip().lower()
        if normalized in BROKEN_PROXY_MARKERS:
            os.environ.pop(key, None)
            cleared.append(key)
    return cleared
