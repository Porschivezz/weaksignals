"""ArXiv API client for ingesting preprints."""

import logging
import re
from datetime import datetime, timezone

import feedparser
import httpx

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"


class ArxivClient:
    """Client for the ArXiv API using Atom feed parsing."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _extract_arxiv_id(entry: dict) -> str:
        """Extract the arXiv ID from an entry's id URL."""
        entry_id = entry.get("id", "")
        match = re.search(r"abs/(.+?)(?:v\d+)?$", entry_id)
        if match:
            return match.group(1)
        return entry_id

    @staticmethod
    def _parse_authors(entry: dict) -> list[dict]:
        """Parse author information from an arXiv feed entry."""
        authors = []
        for author in entry.get("authors", []):
            name = author.get("name", "")
            affiliation = ""
            arxiv_affiliations = author.get("arxiv_affiliation", "")
            if arxiv_affiliations:
                affiliation = arxiv_affiliations
            authors.append({
                "name": name,
                "institution": affiliation,
                "orcid": "",
            })
        return authors

    @staticmethod
    def _parse_categories(entry: dict) -> list[dict]:
        """Parse category tags from an arXiv feed entry as concepts."""
        concepts = []
        tags = entry.get("tags", [])
        for tag in tags:
            term = tag.get("term", "")
            if term:
                concepts.append({
                    "name": term,
                    "score": 1.0,
                })
        return concepts

    @staticmethod
    def _clean_abstract(summary: str) -> str:
        """Clean up an arXiv abstract by removing extra whitespace."""
        if not summary:
            return ""
        cleaned = re.sub(r"\s+", " ", summary).strip()
        return cleaned

    def _normalize_entry(self, entry: dict) -> dict:
        """Normalize an arXiv feed entry to standard dict format."""
        arxiv_id = self._extract_arxiv_id(entry)
        published_str = entry.get("published", "")
        published_date = None
        if published_str:
            try:
                published_date = datetime.fromisoformat(
                    published_str.replace("Z", "+00:00")
                )
            except ValueError:
                logger.warning("Could not parse arXiv date: %s", published_str)

        doi = ""
        links = entry.get("links", [])
        for link in links:
            if link.get("title") == "doi":
                doi = link.get("href", "")
                break

        return {
            "external_id": f"arxiv:{arxiv_id}",
            "title": entry.get("title", "").replace("\n", " ").strip(),
            "abstract": self._clean_abstract(entry.get("summary", "")),
            "authors": self._parse_authors(entry),
            "published_date": published_date,
            "source": "arxiv",
            "concepts": self._parse_categories(entry),
            "cited_by_count": 0,
            "doi": doi,
        }

    async def fetch_recent_papers(
        self,
        category: str = "cs.AI",
        max_results: int = 100,
        start: int = 0,
    ) -> list[dict]:
        """Fetch recent papers from arXiv for a given category."""
        client = await self._get_client()

        search_query = f"cat:{category}"
        params = {
            "search_query": search_query,
            "start": start,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            response = await client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("ArXiv API HTTP error: %s", exc.response.status_code)
            return []
        except httpx.RequestError as exc:
            logger.error("ArXiv API request error: %s", exc)
            return []

        feed = feedparser.parse(response.text)

        if feed.bozo and not feed.entries:
            logger.error("ArXiv feed parse error: %s", feed.bozo_exception)
            return []

        papers = []
        for entry in feed.entries:
            papers.append(self._normalize_entry(entry))

        logger.info(
            "Fetched %d papers from arXiv category '%s'", len(papers), category
        )
        return papers

    async def fetch_paper_by_id(self, arxiv_id: str) -> dict | None:
        """Fetch a single paper by its arXiv ID (e.g., '2301.12345')."""
        client = await self._get_client()

        clean_id = arxiv_id.replace("arxiv:", "")
        params = {
            "id_list": clean_id,
            "max_results": 1,
        }

        try:
            response = await client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("ArXiv fetch by ID HTTP error: %s", exc.response.status_code)
            return None
        except httpx.RequestError as exc:
            logger.error("ArXiv fetch by ID request error: %s", exc)
            return None

        feed = feedparser.parse(response.text)
        if not feed.entries:
            logger.warning("No arXiv entry found for ID: %s", arxiv_id)
            return None

        return self._normalize_entry(feed.entries[0])
