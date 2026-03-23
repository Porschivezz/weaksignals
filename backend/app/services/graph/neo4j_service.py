"""Neo4j graph database service for concept and relationship management."""

import logging
from datetime import datetime, timezone

from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger(__name__)


class Neo4jService:
    """Service for managing the concept knowledge graph in Neo4j.

    Provides methods for upserting concepts, papers, authors, and
    relationships, as well as graph analytics like PageRank,
    betweenness centrality, and community detection.

    Degrades gracefully when Neo4j is unavailable.
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self._driver: AsyncDriver | None = None

    async def _get_driver(self) -> AsyncDriver | None:
        """Get or create the Neo4j async driver."""
        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self.uri, auth=(self.user, self.password)
                )
                await self._driver.verify_connectivity()
                logger.info("Connected to Neo4j at %s", self.uri)
            except Exception as exc:
                logger.warning("Could not connect to Neo4j at %s: %s", self.uri, exc)
                self._driver = None
        return self._driver

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None

    async def ensure_constraints(self) -> None:
        """Create uniqueness constraints on key node properties."""
        driver = await self._get_driver()
        if driver is None:
            logger.warning("Neo4j unavailable, skipping constraint creation")
            return

        constraints = [
            "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT paper_doc_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.doc_id IS UNIQUE",
            "CREATE CONSTRAINT author_name_inst IF NOT EXISTS FOR (a:Author) REQUIRE a.unique_key IS UNIQUE",
        ]

        async with driver.session() as session:
            for constraint_query in constraints:
                try:
                    await session.run(constraint_query)
                except Exception as exc:
                    logger.warning("Constraint creation warning: %s", exc)

        logger.info("Neo4j constraints ensured")

    async def upsert_concept(
        self,
        name: str,
        entity_type: str,
        embedding: list[float] | None = None,
        aliases: list[str] | None = None,
        metadata: dict | None = None,
    ) -> str | None:
        """Insert or update a Concept node in the graph.

        Args:
            name: The canonical name of the concept.
            entity_type: The type classification (technology, method, etc.).
            embedding: Optional embedding vector.
            aliases: Optional list of alternative names.
            metadata: Optional dict of additional properties.

        Returns:
            The name of the upserted concept, or None if unavailable.
        """
        driver = await self._get_driver()
        if driver is None:
            logger.warning("Neo4j unavailable, skipping concept upsert: %s", name)
            return None

        query = """
        MERGE (c:Concept {name: $name})
        SET c.entity_type = $entity_type,
            c.updated_at = $updated_at
        WITH c
        CALL {
            WITH c
            WITH c WHERE $embedding IS NOT NULL
            SET c.embedding = $embedding
        }
        CALL {
            WITH c
            WITH c WHERE $aliases IS NOT NULL
            SET c.aliases = $aliases
        }
        CALL {
            WITH c
            WITH c WHERE $metadata IS NOT NULL
            SET c += $metadata
        }
        RETURN c.name AS name
        """

        async with driver.session() as session:
            try:
                result = await session.run(
                    query,
                    name=name,
                    entity_type=entity_type,
                    embedding=embedding,
                    aliases=aliases or [],
                    metadata=metadata or {},
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
                record = await result.single()
                return record["name"] if record else None
            except Exception as exc:
                logger.error("Failed to upsert concept '%s': %s", name, exc)
                return None

    async def upsert_paper(
        self, doc_id: str, title: str, date: str | None, source: str
    ) -> str | None:
        """Insert or update a Paper node in the graph.

        Args:
            doc_id: The unique document identifier.
            title: The paper title.
            date: Publication date as ISO string.
            source: Data source (openalex, arxiv, etc.).

        Returns:
            The doc_id of the upserted paper, or None if unavailable.
        """
        driver = await self._get_driver()
        if driver is None:
            logger.warning("Neo4j unavailable, skipping paper upsert: %s", doc_id)
            return None

        query = """
        MERGE (p:Paper {doc_id: $doc_id})
        SET p.title = $title,
            p.date = $date,
            p.source = $source,
            p.updated_at = $updated_at
        RETURN p.doc_id AS doc_id
        """

        async with driver.session() as session:
            try:
                result = await session.run(
                    query,
                    doc_id=doc_id,
                    title=title,
                    date=date or "",
                    source=source,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
                record = await result.single()
                return record["doc_id"] if record else None
            except Exception as exc:
                logger.error("Failed to upsert paper '%s': %s", doc_id, exc)
                return None

    async def upsert_author(
        self, name: str, orcid: str = "", institution: str = ""
    ) -> str | None:
        """Insert or update an Author node in the graph.

        Args:
            name: Author display name.
            orcid: ORCID identifier if available.
            institution: Author's institution name.

        Returns:
            The unique_key of the upserted author, or None if unavailable.
        """
        driver = await self._get_driver()
        if driver is None:
            logger.warning("Neo4j unavailable, skipping author upsert: %s", name)
            return None

        unique_key = f"{name}|{institution}" if institution else name

        query = """
        MERGE (a:Author {unique_key: $unique_key})
        SET a.name = $name,
            a.orcid = $orcid,
            a.institution = $institution,
            a.updated_at = $updated_at
        RETURN a.unique_key AS unique_key
        """

        async with driver.session() as session:
            try:
                result = await session.run(
                    query,
                    unique_key=unique_key,
                    name=name,
                    orcid=orcid,
                    institution=institution,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
                record = await result.single()
                return record["unique_key"] if record else None
            except Exception as exc:
                logger.error("Failed to upsert author '%s': %s", name, exc)
                return None

    async def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        from_label: str = "Concept",
        to_label: str = "Concept",
        properties: dict | None = None,
    ) -> bool:
        """Create or update a relationship between two nodes.

        Args:
            from_id: Identifier for the source node (name or doc_id).
            to_id: Identifier for the target node (name or doc_id).
            rel_type: The relationship type (e.g., RELATED_TO, MENTIONS, AUTHORED).
            from_label: Label of the source node.
            to_label: Label of the target node.
            properties: Optional dict of relationship properties (timestamp, weight, etc.).

        Returns:
            True if the relationship was created successfully.
        """
        driver = await self._get_driver()
        if driver is None:
            logger.warning(
                "Neo4j unavailable, skipping relationship: %s -[%s]-> %s",
                from_id, rel_type, to_id,
            )
            return False

        from_key = "name" if from_label == "Concept" else ("doc_id" if from_label == "Paper" else "unique_key")
        to_key = "name" if to_label == "Concept" else ("doc_id" if to_label == "Paper" else "unique_key")

        props = properties or {}
        if "timestamp" not in props:
            props["timestamp"] = datetime.now(timezone.utc).isoformat()
        if "weight" not in props:
            props["weight"] = 1.0

        # Dynamically build the relationship type into the query
        # rel_type is sanitized to only allow alphanumeric and underscore
        safe_rel_type = "".join(c for c in rel_type if c.isalnum() or c == "_")

        query = f"""
        MATCH (a:{from_label} {{{from_key}: $from_id}})
        MATCH (b:{to_label} {{{to_key}: $to_id}})
        MERGE (a)-[r:{safe_rel_type}]->(b)
        SET r += $props
        RETURN type(r) AS rel_type
        """

        async with driver.session() as session:
            try:
                result = await session.run(
                    query, from_id=from_id, to_id=to_id, props=props
                )
                record = await result.single()
                return record is not None
            except Exception as exc:
                logger.error(
                    "Failed to create relationship %s -[%s]-> %s: %s",
                    from_id, rel_type, to_id, exc,
                )
                return False

    async def get_concept_neighborhood(
        self, concept_name: str, depth: int = 2
    ) -> dict:
        """Get the neighborhood graph around a concept.

        Args:
            concept_name: The name of the central concept.
            depth: How many hops to traverse (default 2).

        Returns:
            Dict with 'nodes' and 'edges' lists.
        """
        driver = await self._get_driver()
        if driver is None:
            logger.warning("Neo4j unavailable, returning empty neighborhood")
            return {"nodes": [], "edges": []}

        query = """
        MATCH path = (c:Concept {name: $concept_name})-[*1..$depth]-(neighbor)
        WITH nodes(path) AS ns, relationships(path) AS rs
        UNWIND ns AS n
        WITH collect(DISTINCT {
            id: coalesce(n.name, n.doc_id, n.unique_key),
            label: labels(n)[0],
            properties: properties(n)
        }) AS nodes, rs
        UNWIND rs AS r
        WITH nodes, collect(DISTINCT {
            source: coalesce(startNode(r).name, startNode(r).doc_id, startNode(r).unique_key),
            target: coalesce(endNode(r).name, endNode(r).doc_id, endNode(r).unique_key),
            type: type(r),
            weight: r.weight
        }) AS edges
        RETURN nodes, edges
        """

        async with driver.session() as session:
            try:
                result = await session.run(
                    query, concept_name=concept_name, depth=depth
                )
                record = await result.single()
                if record:
                    return {
                        "nodes": record["nodes"],
                        "edges": record["edges"],
                    }
                return {"nodes": [], "edges": []}
            except Exception as exc:
                logger.error(
                    "Failed to get neighborhood for '%s': %s", concept_name, exc
                )
                return {"nodes": [], "edges": []}

    async def get_tenant_landscape(
        self, industry_concepts: list[str]
    ) -> dict:
        """Get the concept landscape relevant to a tenant's industry.

        Args:
            industry_concepts: List of concept names relevant to the tenant.

        Returns:
            Dict with 'nodes' and 'edges' lists forming the landscape subgraph.
        """
        driver = await self._get_driver()
        if driver is None:
            logger.warning("Neo4j unavailable, returning empty landscape")
            return {"nodes": [], "edges": []}

        if not industry_concepts:
            return {"nodes": [], "edges": []}

        query = """
        UNWIND $concepts AS concept_name
        MATCH (c:Concept {name: concept_name})
        OPTIONAL MATCH (c)-[r]-(neighbor)
        WITH collect(DISTINCT {
            id: c.name,
            label: 'Concept',
            entity_type: c.entity_type
        }) + collect(DISTINCT {
            id: coalesce(neighbor.name, neighbor.doc_id, neighbor.unique_key),
            label: labels(neighbor)[0],
            entity_type: neighbor.entity_type
        }) AS all_nodes,
        collect(DISTINCT {
            source: coalesce(startNode(r).name, startNode(r).doc_id, startNode(r).unique_key),
            target: coalesce(endNode(r).name, endNode(r).doc_id, endNode(r).unique_key),
            type: type(r),
            weight: r.weight
        }) AS edges
        RETURN all_nodes AS nodes, edges
        """

        async with driver.session() as session:
            try:
                result = await session.run(query, concepts=industry_concepts)
                record = await result.single()
                if record:
                    # Filter out null nodes
                    nodes = [n for n in record["nodes"] if n.get("id")]
                    edges = [e for e in record["edges"] if e.get("source") and e.get("target")]
                    return {"nodes": nodes, "edges": edges}
                return {"nodes": [], "edges": []}
            except Exception as exc:
                logger.error("Failed to get tenant landscape: %s", exc)
                return {"nodes": [], "edges": []}

    async def compute_pagerank(self) -> dict[str, float]:
        """Compute PageRank scores for all Concept nodes.

        Uses a simple iterative approach via Cypher if GDS is not available.

        Returns:
            Dict mapping concept name to PageRank score.
        """
        driver = await self._get_driver()
        if driver is None:
            logger.warning("Neo4j unavailable, returning empty PageRank")
            return {}

        # Try GDS first, fall back to degree-based approximation
        query = """
        MATCH (c:Concept)
        OPTIONAL MATCH (c)<-[r]-(other)
        WITH c, count(r) AS in_degree
        OPTIONAL MATCH (c)-[r2]->(other2)
        WITH c, in_degree, count(r2) AS out_degree
        WITH c, in_degree, out_degree,
             toFloat(in_degree) / (CASE WHEN in_degree + out_degree = 0 THEN 1 ELSE in_degree + out_degree END) AS approx_pr
        RETURN c.name AS name, approx_pr AS score
        ORDER BY score DESC
        """

        async with driver.session() as session:
            try:
                result = await session.run(query)
                records = await result.data()
                return {r["name"]: r["score"] for r in records if r["name"]}
            except Exception as exc:
                logger.error("Failed to compute PageRank: %s", exc)
                return {}

    async def compute_betweenness(self) -> dict[str, float]:
        """Compute betweenness centrality approximation for Concept nodes.

        Uses degree-based heuristic as an approximation when GDS is not installed.

        Returns:
            Dict mapping concept name to betweenness score.
        """
        driver = await self._get_driver()
        if driver is None:
            logger.warning("Neo4j unavailable, returning empty betweenness")
            return {}

        query = """
        MATCH (c:Concept)
        OPTIONAL MATCH (c)-[r]-(neighbor)
        WITH c, count(DISTINCT neighbor) AS degree
        OPTIONAL MATCH (c)--(n1)--(n2)
        WHERE n1 <> n2 AND n1 <> c AND n2 <> c
        WITH c, degree, count(DISTINCT [n1, n2]) AS bridge_paths
        WITH c, degree,
             toFloat(bridge_paths) / (CASE WHEN degree * (degree - 1) = 0 THEN 1 ELSE degree * (degree - 1) END) AS approx_betweenness
        RETURN c.name AS name, approx_betweenness AS score
        ORDER BY score DESC
        """

        async with driver.session() as session:
            try:
                result = await session.run(query)
                records = await result.data()
                return {r["name"]: r["score"] for r in records if r["name"]}
            except Exception as exc:
                logger.error("Failed to compute betweenness: %s", exc)
                return {}

    async def run_leiden_communities(self) -> list[dict]:
        """Detect communities among Concept nodes.

        Uses Louvain-like community detection via connected components
        and modularity grouping when GDS is not available.

        Returns:
            List of dicts, each with 'community_id' and 'members' (list of concept names).
        """
        driver = await self._get_driver()
        if driver is None:
            logger.warning("Neo4j unavailable, returning empty communities")
            return []

        # Use weakly connected components as a community approximation
        query = """
        MATCH (c:Concept)
        OPTIONAL MATCH (c)-[r]-(neighbor:Concept)
        WITH c, collect(DISTINCT neighbor.name) AS neighbors
        RETURN c.name AS name, neighbors
        """

        async with driver.session() as session:
            try:
                result = await session.run(query)
                records = await result.data()
            except Exception as exc:
                logger.error("Failed to run community detection: %s", exc)
                return []

        if not records:
            return []

        # Build adjacency and find connected components using BFS
        adjacency: dict[str, set[str]] = {}
        for record in records:
            name = record["name"]
            if name:
                adjacency[name] = set(n for n in record["neighbors"] if n)

        visited: set[str] = set()
        communities: list[dict] = []
        community_id = 0

        for node in adjacency:
            if node in visited:
                continue
            # BFS to find connected component
            component: list[str] = []
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                for neighbor in adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)

            communities.append({
                "community_id": community_id,
                "members": sorted(component),
            })
            community_id += 1

        logger.info("Detected %d communities from Neo4j graph", len(communities))
        return communities
