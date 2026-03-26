"""PubMed / NCBI E-utilities client for ingesting biomedical literature."""

import logging
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class PubMedClient:
    """Client for NCBI E-utilities (PubMed)."""

    def __init__(self, email: str = "weaksignals@huginnmuninn.tech"):
        self.email = email
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def search_and_fetch(
        self,
        query: str,
        max_results: int = 50,
        days_back: int = 30,
    ) -> list[dict]:
        """Search PubMed and fetch article details."""
        client = await self._get_client()

        from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y/%m/%d")
        to_date = datetime.now(timezone.utc).strftime("%Y/%m/%d")

        # Step 1: Search for PMIDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "date",
            "datetype": "pdat",
            "mindate": from_date,
            "maxdate": to_date,
            "tool": "weaksignals",
            "email": self.email,
        }

        try:
            resp = await client.get(ESEARCH_URL, params=search_params)
            resp.raise_for_status()
            search_data = resp.json()
        except Exception as exc:
            logger.error("PubMed search failed: %s", exc)
            return []

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            logger.info("PubMed: no results for query '%s'", query)
            return []

        # Step 2: Fetch article details in XML
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml",
            "rettype": "abstract",
            "tool": "weaksignals",
            "email": self.email,
        }

        try:
            resp = await client.get(EFETCH_URL, params=fetch_params)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("PubMed fetch failed: %s", exc)
            return []

        return self._parse_xml(resp.text)

    def _parse_xml(self, xml_text: str) -> list[dict]:
        """Parse PubMed XML response into normalized dicts."""
        from lxml import etree

        articles = []
        try:
            root = etree.fromstring(xml_text.encode("utf-8"))
        except Exception as exc:
            logger.error("Failed to parse PubMed XML: %s", exc)
            return []

        for article_el in root.findall(".//PubmedArticle"):
            try:
                medline = article_el.find("MedlineCitation")
                if medline is None:
                    continue

                pmid_el = medline.find("PMID")
                pmid = pmid_el.text if pmid_el is not None else ""

                art = medline.find("Article")
                if art is None:
                    continue

                title_el = art.find("ArticleTitle")
                title = title_el.text if title_el is not None else ""
                if not title:
                    continue

                abstract_parts = []
                abstract_el = art.find("Abstract")
                if abstract_el is not None:
                    for at in abstract_el.findall("AbstractText"):
                        label = at.get("Label", "")
                        text = "".join(at.itertext())
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
                abstract = " ".join(abstract_parts)

                # Authors
                authors = []
                author_list = art.find("AuthorList")
                if author_list is not None:
                    for author_el in author_list.findall("Author"):
                        last = author_el.findtext("LastName", "")
                        fore = author_el.findtext("ForeName", "")
                        name = f"{fore} {last}".strip()
                        affil_el = author_el.find(".//Affiliation")
                        affil = affil_el.text if affil_el is not None else ""
                        if name:
                            authors.append({
                                "name": name,
                                "institution": affil,
                                "orcid": "",
                            })

                # Date
                pub_date = None
                pd_el = art.find(".//PubDate")
                if pd_el is not None:
                    year = pd_el.findtext("Year", "")
                    month = pd_el.findtext("Month", "01")
                    day = pd_el.findtext("Day", "01")
                    month_map = {
                        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
                    }
                    if month in month_map:
                        month = month_map[month]
                    if year:
                        try:
                            pub_date = datetime(
                                int(year), int(month), int(day), tzinfo=timezone.utc
                            )
                        except (ValueError, TypeError):
                            try:
                                pub_date = datetime(int(year), 1, 1, tzinfo=timezone.utc)
                            except (ValueError, TypeError):
                                pass

                # MeSH terms as concepts
                concepts = []
                mesh_list = medline.find("MeshHeadingList")
                if mesh_list is not None:
                    for mesh in mesh_list.findall("MeshHeading"):
                        desc = mesh.find("DescriptorName")
                        if desc is not None and desc.text:
                            concepts.append({
                                "name": desc.text,
                                "score": 1.0,
                            })

                articles.append({
                    "external_id": f"pmid:{pmid}",
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "published_date": pub_date,
                    "source": "pubmed",
                    "concepts": concepts,
                    "cited_by_count": 0,
                    "doi": "",
                })
            except Exception as exc:
                logger.warning("Failed to parse PubMed article: %s", exc)
                continue

        logger.info("Parsed %d articles from PubMed", len(articles))
        return articles
