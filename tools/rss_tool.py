from datetime import datetime, timedelta, timezone

from core.network_utils import clear_broken_local_proxies
from core.topic_utils import topic_keywords

try:
    import feedparser
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    feedparser = None


clear_broken_local_proxies()

RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.reuters.com/reuters/topNews",
    "https://www.thehindu.com/feeder/default.rss",
    "https://indianexpress.com/feed/",
]


def rss_fetch(topic: str, hours_back: int = 24) -> list:
    """
    Fetches topic-matching articles from configured RSS feeds.
    Returns normalized article dicts.
    """
    if feedparser is None:
        return []

    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    keywords = topic_keywords(topic)

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                if published and published < cutoff:
                    continue

                text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                if keywords and not any(keyword in text for keyword in keywords):
                    continue

                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "content": entry.get("summary", ""),
                        "source": "rss",
                        "published": published.isoformat() if published else "",
                    }
                )
        except Exception as exc:
            print(f"[RSS] Feed error {feed_url}: {exc}")

    return articles
