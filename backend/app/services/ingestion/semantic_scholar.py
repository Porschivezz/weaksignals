"""Semantic Scholar API client for ingesting academic papers."""

import logging
from datetime import datetime, timezone

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.semanticscholar.org/graph/v1"

DEFAULT_FIELDS = (
    "paperId,externalIds,title,abstract,authors,year,"
    "citationCount,fieldsOfStudy,publicationDate,journal"
)

AUTHOR_FIELDS = "authorId,name,affiliations"


class RateLimitError(Exception):
    """Raised when the Semantic Scholar API rate limit is hit."""


class SemanticScholarClient:
    """Client for the Semantic Scholar Graph API with retry logic."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=30.0,
                headers=headers,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _normalize_paper(self, paper: dict) -> dict:
        """Normalize a Semantic Scholar paper to standard dict format."""
        authors = []
        for author in paper.get("authors", []):
            affiliations = author.get("affiliations") or []
            institution = affiliations[0] if affiliations else ""
            authors.append({
                "name": author.get("name", ""),
                "institution": institution,
                "orcid": "",
            })

        external_ids = paper.get("externalIds") or {}
        doi = external_ids.get("DOI", "")
        arxiv_id = external_ids.get("ArXiv", "")
        paper_id = paper.get("paperId", "")

        external_id = f"s2:{paper_id}"
        if arxiv_id:
            external_id = f"arxiv:{arxiv_id}"

        published_date = None
        pub_date_str = paper.get("publicationDate")
        if pub_date_str:
            try:
                published_date = datetime.strptime(pub_date_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                logger.warning("Could not parse S2 date: %s", pub_date_str)

        concepts = []
        for field in paper.get("fieldsOfStudy") or []:
            concepts.append({
                "name": field,
                "score": 1.0,
            })

        return {
            "external_id": external_id,
            "title": paper.get("title") or "",
            "abstract": paper.get("abstract") or "",
            "authors": authors,
            "published_date": published_date,
            "source": "semantic_scholar",
            "concepts": concepts,
            "cited_by_count": paper.get("citationCount", 0),
            "doi": doi,
        }

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _request(
        self, method: str, url: str, **kwargs: object
    ) -> httpx.Response:
        """Make an API request with rate-limit retry."""
        client = await self._get_client()
        response = await client.request(method, url, **kwargs)

        if response.status_code == 429:
            logger.warning("Semantic Scholar rate limit hit, retrying...")
            raise RateLimitError("Rate limit exceeded")

        response.raise_for_status()
        return response

    async def fetch_papers(
        self,
        query: str,
        limit: int = 100,
        fields: str = DEFAULT_FIELDS,
        offset: int = 0,
    ) -> list[dict]:
        """Search for papers matching a query string."""
        all_papers: list[dict] = []
        current_offset = offset
        remaining = limit

        while remaining > 0:
            batch_size = min(remaining, 100)
            params = {
                "query": query,
                "limit": batch_size,
                "offset": current_offset,
                "fields": fields,
            }

            try:
                response = await self._request("GET", "/paper/search", params=params)
                data = response.json()
            except RateLimitError:
                logger.error("Semantic Scholar rate limit exhausted after retries")
                break
            except httpx.HTTPStatusError as exc:
                logger.error("Semantic Scholar HTTP error: %s", exc.response.status_code)
                break
            except httpx.RequestError as exc:
                logger.error("Semantic Scholar request error: %s", exc)
                break

            papers = data.get("data", [])
            if not papers:
                break

            for paper in papers:
                all_papers.append(self._normalize_paper(paper))

            total = data.get("total", 0)
            current_offset += batch_size
            remaining -= batch_size

            if current_offset >= total:
                break

        logger.info(
            "Fetched %d papers from Semantic Scholar for query '%s'",
            len(all_papers),
            query,
        )
        return all_papers

    async def fetch_paper_details(self, paper_id: str) -> dict | None:
        """Fetch detailed information about a specific paper."""
        fields = f"{DEFAULT_FIELDS},references,citations"
        params = {"fields": fields}

        try:
            response = await self._request(
                "GET", f"/paper/{paper_id}", params=params
            )
            data = response.json()
            return self._normalize_paper(data)
        except RateLimitError:
            logger.error("Rate limit exhausted fetching paper %s", paper_id)
            return None
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Semantic Scholar fetch paper detail error: %s",
                exc.response.status_code,
            )
            return None
        except httpx.RequestError as exc:
            logger.error("Semantic Scholar fetch paper detail request error: %s", exc)
            return None
