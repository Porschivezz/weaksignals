from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from neo4j import AsyncGraphDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/landscape", tags=["landscape"])


async def _get_neo4j_driver():
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    return driver


@router.get("", response_model=dict[str, Any])
async def get_landscape(
    depth: int = Query(2, ge=1, le=4, description="Graph traversal depth"),
    limit: int = Query(100, ge=1, le=500, description="Max nodes to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return graph data (nodes + edges) for the tenant's industry landscape."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    verticals = tenant.industry_verticals or []
    watchlist = tenant.technology_watchlist or []
    seed_terms = verticals + watchlist

    if not seed_terms:
        return {"nodes": [], "edges": [], "meta": {"message": "No industry verticals or watchlist configured"}}

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    try:
        driver = await _get_neo4j_driver()
        async with driver.session() as session:
            # Query for entities connected to seed terms within depth hops
            query = """
            MATCH (seed:Entity)
            WHERE seed.name IN $seed_terms
            CALL apoc.path.subgraphAll(seed, {
                maxLevel: $depth,
                limit: $limit
            })
            YIELD nodes AS n, relationships AS r
            RETURN n, r
            """
            # Fallback query if APOC is not available
            fallback_query = """
            MATCH (e:Entity)
            WHERE e.name IN $seed_terms
            OPTIONAL MATCH (e)-[r]-(connected)
            RETURN
                collect(DISTINCT {
                    id: elementId(e),
                    name: e.name,
                    type: labels(e)[0],
                    properties: properties(e)
                }) +
                collect(DISTINCT {
                    id: elementId(connected),
                    name: connected.name,
                    type: labels(connected)[0],
                    properties: properties(connected)
                }) AS nodes,
                collect(DISTINCT {
                    source: elementId(startNode(r)),
                    target: elementId(endNode(r)),
                    type: type(r),
                    properties: properties(r)
                }) AS edges
            """
            try:
                result = await session.run(
                    fallback_query,
                    seed_terms=seed_terms,
                )
                record = await result.single()
                if record:
                    raw_nodes = record["nodes"] or []
                    raw_edges = record["edges"] or []
                    # Deduplicate nodes by id
                    seen_ids: set[str] = set()
                    for n in raw_nodes:
                        if n and n.get("id") and n["id"] not in seen_ids:
                            seen_ids.add(n["id"])
                            nodes.append({
                                "id": n["id"],
                                "label": n.get("name", ""),
                                "type": n.get("type", "Entity"),
                            })
                    for e in raw_edges:
                        if e and e.get("source"):
                            edges.append({
                                "source": e["source"],
                                "target": e["target"],
                                "type": e.get("type", "RELATED_TO"),
                            })
            except Exception:
                # If Neo4j query fails (e.g. empty database), return empty graph
                pass
        await driver.close()
    except Exception:
        # Neo4j might not be available; return empty graph
        return {
            "nodes": [],
            "edges": [],
            "meta": {"message": "Graph database unavailable"},
        }

    return {
        "nodes": nodes[:limit],
        "edges": edges,
        "meta": {"seed_terms": seed_terms, "depth": depth},
    }


@router.get("/competitors", response_model=dict[str, Any])
async def get_competitor_analysis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Competitor analysis based on tenant's competitor list and graph data."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    competitor_list = tenant.competitor_list or {}
    competitors = competitor_list.get("names", []) if isinstance(competitor_list, dict) else []

    if not competitors:
        return {
            "competitors": [],
            "shared_technologies": [],
            "meta": {"message": "No competitors configured for this tenant"},
        }

    competitor_data: list[dict[str, Any]] = []

    try:
        driver = await _get_neo4j_driver()
        async with driver.session() as session:
            query = """
            MATCH (c:Organization)
            WHERE c.name IN $competitors
            OPTIONAL MATCH (c)-[:RESEARCHES|PUBLISHES|USES]->(tech:Technology)
            RETURN c.name AS competitor,
                   collect(DISTINCT tech.name) AS technologies
            """
            try:
                result = await session.run(query, competitors=competitors)
                records = await result.data()
                all_techs: list[set[str]] = []
                for rec in records:
                    techs = rec.get("technologies", [])
                    tech_set = {t for t in techs if t}
                    all_techs.append(tech_set)
                    competitor_data.append({
                        "name": rec["competitor"],
                        "technologies": list(tech_set),
                        "technology_count": len(tech_set),
                    })

                # Find shared technologies (appearing in 2+ competitors)
                from collections import Counter
                tech_counter: Counter[str] = Counter()
                for ts in all_techs:
                    for t in ts:
                        tech_counter[t] += 1
                shared = [
                    {"technology": tech, "competitor_count": count}
                    for tech, count in tech_counter.most_common()
                    if count >= 2
                ]
            except Exception:
                shared = []
        await driver.close()
    except Exception:
        # Return competitor names without graph enrichment
        competitor_data = [{"name": c, "technologies": [], "technology_count": 0} for c in competitors]
        shared = []

    return {
        "competitors": competitor_data,
        "shared_technologies": shared,
        "meta": {"total_competitors": len(competitors)},
    }
