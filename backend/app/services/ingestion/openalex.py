"""OpenAlex API client for ingesting academic works."""

import logging
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org"


class OpenAlexClient:
    """Client for the OpenAlex API with polite pool support."""

    def __init__(self, email: str = "weaksignals@example.com"):
        self.email = email
        self.base_url = BASE_URL
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={"User-Agent": f"WeakSignals/1.0 (mailto:{self.email})"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _normalize_work(self, work: dict) -> dict:
        """Normalize an OpenAlex work record to a standard dict format."""
        authors = []
        for authorship in work.get("authorships", []):
            author_info = authorship.get("author", {})
            institutions = authorship.get("institutions", [])
            institution_name = institutions[0].get("display_name", "") if institutions else ""
            authors.append({
                "name": author_info.get("display_name", ""),
                "institution": institution_name,
                "orcid": author_info.get("orcid") or "",
            })

        abstract_index = work.get("abstract_inverted_index")
        abstract = self._reconstruct_abstract(abstract_index) if abstract_index else ""

        concepts = []
        for concept in work.get("concepts", []):
            concepts.append({
                "name": concept.get("display_name", ""),
                "score": concept.get("score", 0.0),
            })

        published_date_str = work.get("publication_date")
        published_date = None
        if published_date_str:
            try:
                published_date = datetime.strptime(published_date_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                logger.warning("Could not parse date: %s", published_date_str)

        return {
            "external_id": work.get("id", ""),
            "title": work.get("title", ""),
            "abstract": abstract,
            "authors": authors,
            "published_date": published_date,
            "source": "openalex",
            "concepts": concepts,
            "cited_by_count": work.get("cited_by_count", 0),
            "doi": work.get("doi") or "",
        }

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict) -> str:
        """Reconstruct abstract text from OpenAlex inverted index format."""
        if not inverted_index:
            return ""
        word_positions: list[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort(key=lambda x: x[0])
        return " ".join(word for _, word in word_positions)

    async def fetch_recent_works(
        self,
        query: str = "artificial intelligence",
        per_page: int = 50,
        from_date: datetime | None = None,
        max_pages: int = 5,
    ) -> list[dict]:
        """Fetch recent works matching a query with cursor-based pagination."""
        if from_date is None:
            from_date = datetime.now(timezone.utc) - timedelta(days=30)

        client = await self._get_client()
        date_str = from_date.strftime("%Y-%m-%d")

        all_works: list[dict] = []
        cursor = "*"

        for page_num in range(max_pages):
            params: dict = {
                "search": query,
                "filter": f"from_publication_date:{date_str}",
                "per_page": per_page,
                "cursor": cursor,
                "mailto": self.email,
            }

            try:
                response = await client.get("/works", params=params)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "OpenAlex API HTTP error on page %d: %s", page_num, exc.response.status_code
                )
                break
            except httpx.RequestError as exc:
                logger.error("OpenAlex API request error on page %d: %s", page_num, exc)
                break

            results = data.get("results", [])
            if not results:
                break

            for work in results:
                all_works.append(self._normalize_work(work))

            next_cursor = data.get("meta", {}).get("next_cursor")
            if not next_cursor:
                break
            cursor = next_cursor

        logger.info("Fetched %d works from OpenAlex for query '%s'", len(all_works), query)
        return all_works

    async def fetch_work_by_id(self, openalex_id: str) -> dict | None:
        """Fetch a single work by its OpenAlex ID."""
        client = await self._get_client()
        clean_id = openalex_id
        if openalex_id.startswith("https://openalex.org/"):
            clean_id = openalex_id.replace("https://openalex.org/", "")

        try:
            response = await client.get(f"/works/{clean_id}", params={"mailto": self.email})
            response.raise_for_status()
            return self._normalize_work(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAlex fetch by ID error: %s", exc.response.status_code)
            return None
        except httpx.RequestError as exc:
            logger.error("OpenAlex fetch by ID request error: %s", exc)
            return None

    async def search_concepts(self, query: str, per_page: int = 25) -> list[dict]:
        """Search OpenAlex concepts by query string."""
        client = await self._get_client()

        try:
            response = await client.get(
                "/concepts",
                params={
                    "search": query,
                    "per_page": per_page,
                    "mailto": self.email,
                },
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAlex concepts search HTTP error: %s", exc.response.status_code)
            return []
        except httpx.RequestError as exc:
            logger.error("OpenAlex concepts search request error: %s", exc)
            return []

        concepts = []
        for concept in data.get("results", []):
            concepts.append({
                "id": concept.get("id", ""),
                "name": concept.get("display_name", ""),
                "level": concept.get("level", 0),
                "works_count": concept.get("works_count", 0),
                "description": concept.get("description", ""),
                "wikidata_id": concept.get("wikidata") or "",
            })

        logger.info("Found %d concepts for query '%s'", len(concepts), query)
        return concepts
