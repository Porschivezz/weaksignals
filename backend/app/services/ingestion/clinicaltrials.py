"""ClinicalTrials.gov API v2 client for ingesting clinical trial data."""

import logging
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://clinicaltrials.gov/api/v2"


class ClinicalTrialsClient:
    """Client for ClinicalTrials.gov API v2."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def search_studies(
        self,
        query: str,
        max_results: int = 50,
        days_back: int = 90,
    ) -> list[dict]:
        """Search for clinical trials and return normalized results."""
        client = await self._get_client()

        from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

        params = {
            "query.term": query,
            "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{from_date},MAX]",
            "pageSize": min(max_results, 100),
            "format": "json",
            "fields": "NCTId,BriefTitle,OfficialTitle,BriefSummary,Condition,InterventionName,InterventionType,Phase,OverallStatus,StartDate,PrimaryCompletionDate,LeadSponsorName,CollaboratorName,LastUpdatePostDate,StudyType",
        }

        try:
            resp = await client.get(f"{BASE_URL}/studies", params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error("ClinicalTrials.gov search failed: %s", exc)
            return []

        studies = data.get("studies", [])
        results = []

        for study in studies:
            try:
                proto = study.get("protocolSection", {})
                ident = proto.get("identificationModule", {})
                desc = proto.get("descriptionModule", {})
                status_mod = proto.get("statusModule", {})
                sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
                arms_mod = proto.get("armsInterventionsModule", {})
                conditions_mod = proto.get("conditionsModule", {})
                design_mod = proto.get("designModule", {})

                nct_id = ident.get("nctId", "")
                title = ident.get("officialTitle") or ident.get("briefTitle", "")
                summary = desc.get("briefSummary", "")

                # Sponsor as author
                authors = []
                lead_sponsor = sponsor_mod.get("leadSponsor", {})
                if lead_sponsor.get("name"):
                    authors.append({
                        "name": lead_sponsor["name"],
                        "institution": lead_sponsor.get("class", ""),
                        "orcid": "",
                    })
                for collab in sponsor_mod.get("collaborators", []):
                    if collab.get("name"):
                        authors.append({
                            "name": collab["name"],
                            "institution": collab.get("class", ""),
                            "orcid": "",
                        })

                # Date
                pub_date = None
                date_str = status_mod.get("lastUpdatePostDateStruct", {}).get("date")
                if date_str:
                    try:
                        pub_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except ValueError:
                        try:
                            pub_date = datetime.strptime(date_str, "%Y-%m").replace(tzinfo=timezone.utc)
                        except ValueError:
                            pass

                # Conditions + interventions as concepts
                concepts = []
                for cond in conditions_mod.get("conditions", []):
                    concepts.append({"name": cond, "score": 1.0})

                interventions = arms_mod.get("interventions", [])
                for interv in interventions:
                    name = interv.get("name", "")
                    if name:
                        concepts.append({"name": name, "score": 0.9})

                phase = design_mod.get("phases", [])
                status = status_mod.get("overallStatus", "")

                results.append({
                    "external_id": f"nct:{nct_id}",
                    "title": title,
                    "abstract": summary,
                    "authors": authors,
                    "published_date": pub_date,
                    "source": "clinicaltrials",
                    "concepts": concepts,
                    "cited_by_count": 0,
                    "doi": "",
                    "metadata_extra": {
                        "nct_id": nct_id,
                        "phase": phase,
                        "status": status,
                        "conditions": conditions_mod.get("conditions", []),
                        "interventions": [i.get("name", "") for i in interventions],
                    },
                })
            except Exception as exc:
                logger.warning("Failed to parse clinical trial: %s", exc)
                continue

        logger.info("Fetched %d studies from ClinicalTrials.gov for '%s'", len(results), query)
        return results
