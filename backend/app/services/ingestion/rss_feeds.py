"""RSS feed client for pharma/biotech industry news."""

import hashlib
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

logger = logging.getLogger(__name__)

# Pharma-relevant RSS feeds
PHARMA_FEEDS = [
    {
        "url": "https://www.statnews.com/feed/",
        "name": "STAT News",
        "category": "pharma_news",
    },
    {
        "url": "https://www.fiercepharma.com/rss/xml",
        "name": "Fierce Pharma",
        "category": "pharma_news",
    },
    {
        "url": "https://www.drugdiscoverynews.com/rss",
        "name": "Drug Discovery News",
        "category": "drug_discovery",
    },
    {
        "url": "https://www.nature.com/nrd.rss",
        "name": "Nature Reviews Drug Discovery",
        "category": "research",
    },
    {
        "url": "https://www.nature.com/nbt.rss",
        "name": "Nature Biotechnology",
        "category": "biotech",
    },
    {
        "url": "https://pharmvestnik.ru/rss",
        "name": "Фармацевтический Вестник",
        "category": "pharma_ru",
    },
]


class RSSFeedClient:
    """Client for fetching and parsing pharma-related RSS feeds."""

    def __init__(self, feeds: list[dict] | None = None):
        self.feeds = feeds or PHARMA_FEEDS
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
                headers={"User-Agent": "WeakSignals/1.0 (HuginnMuninn)"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def fetch_all_feeds(self) -> list[dict]:
        """Fetch and parse all configured RSS feeds."""
        all_articles = []
        client = await self._get_client()

        for feed_config in self.feeds:
            try:
                resp = await client.get(feed_config["url"])
                resp.raise_for_status()
                parsed = feedparser.parse(resp.text)

                for entry in parsed.entries[:20]:  # Limit per feed
                    article = self._normalize_entry(entry, feed_config)
                    if article:
                        all_articles.append(article)

            except Exception as exc:
                logger.warning(
                    "Failed to fetch RSS feed '%s': %s",
                    feed_config["name"], exc,
                )
                continue

        logger.info("Fetched %d articles from %d RSS feeds", len(all_articles), len(self.feeds))
        return all_articles

    def _normalize_entry(self, entry: dict, feed_config: dict) -> dict | None:
        """Normalize an RSS entry to standard document format."""
        title = entry.get("title", "").strip()
        if not title:
            return None

        link = entry.get("link", "")
        summary = entry.get("summary", "") or entry.get("description", "")
        # Strip HTML tags from summary
        import re
        summary = re.sub(r"<[^>]+>", "", summary).strip()
        summary = re.sub(r"\s+", " ", summary)

        # Generate stable external_id from link or title
        ext_id = link if link else title
        hash_id = hashlib.md5(ext_id.encode()).hexdigest()
        external_id = f"rss:{feed_config['name']}:{hash_id}"

        # Parse date
        pub_date = None
        if entry.get("published_parsed"):
            try:
                import time
                pub_date = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed),
                    tz=timezone.utc,
                )
            except Exception:
                pass
        elif entry.get("published"):
            try:
                pub_date = parsedate_to_datetime(entry["published"])
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        if pub_date is None:
            pub_date = datetime.now(timezone.utc)

        # Author
        authors = []
        author = entry.get("author", "")
        if author:
            authors.append({"name": author, "institution": "", "orcid": ""})

        return {
            "external_id": external_id,
            "title": title,
            "abstract": summary[:2000] if summary else "",
            "authors": authors,
            "published_date": pub_date,
            "source": "rss",
            "concepts": [],
            "cited_by_count": 0,
            "doi": "",
            "metadata_extra": {
                "feed_name": feed_config["name"],
                "feed_category": feed_config["category"],
                "url": link,
            },
        }
