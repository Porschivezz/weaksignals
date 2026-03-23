"""Celery tasks for the weak signals pipeline.

All tasks use synchronous database sessions since Celery workers
do not run an asyncio event loop by default. Async API clients
are run via asyncio.run() within each task.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.document import Document, DocumentSource
from app.models.entity import DocumentEntity, Entity, EntityType, ExtractionMethod
from app.models.signal import Signal, SignalStatus, SignalType, TenantSignal
from app.models.tenant import Tenant
from app.services.detection.community import CommunityDetector
from app.services.detection.momentum import MomentumAnalyzer
from app.services.detection.novelty import NoveltyDetector
from app.services.detection.scoring import SignalScorer
from app.services.ingestion.arxiv import ArxivClient
from app.services.ingestion.openalex import OpenAlexClient
from app.services.nlp.embeddings import EmbeddingService
from app.services.nlp.extractor import EntityExtractor
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Sync engine and session factory for Celery workers
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
SyncSessionFactory = sessionmaker(bind=sync_engine, expire_on_commit=False)


def _get_sync_session() -> Session:
    """Create a new synchronous database session."""
    return SyncSessionFactory()


def _get_embedding_service() -> EmbeddingService:
    """Create an EmbeddingService instance."""
    api_key = settings.COHERE_API_KEY or None
    return EmbeddingService(api_key=api_key if api_key else None)


def _get_entity_extractor() -> EntityExtractor:
    """Create an EntityExtractor instance."""
    return EntityExtractor()


def _map_entity_type(raw_type: str) -> EntityType:
    """Map a raw entity type string to the EntityType enum."""
    mapping = {
        "technology": EntityType.technology,
        "method": EntityType.method,
        "algorithm": EntityType.algorithm,
        "framework": EntityType.framework,
        "material": EntityType.material,
    }
    return mapping.get(raw_type.lower(), EntityType.technology)


def _store_documents(session: Session, works: list[dict], source: DocumentSource) -> list[Document]:
    """Store normalized works as Document records, deduplicating by external_id.

    Args:
        session: SQLAlchemy sync session.
        works: List of normalized work dicts.
        source: The DocumentSource enum value.

    Returns:
        List of newly created Document objects.
    """
    new_docs: list[Document] = []

    for work in works:
        external_id = work.get("external_id", "")
        if not external_id:
            continue

        existing = session.execute(
            select(Document).where(Document.external_id == external_id)
        ).scalar_one_or_none()

        if existing is not None:
            continue

        doc = Document(
            id=uuid.uuid4(),
            external_id=external_id,
            source=source,
            title=work.get("title", ""),
            abstract=work.get("abstract", ""),
            authors=work.get("authors"),
            published_date=work.get("published_date"),
            metadata_={"concepts": work.get("concepts", []),
                        "cited_by_count": work.get("cited_by_count", 0),
                        "doi": work.get("doi", "")},
            processed=False,
        )
        session.add(doc)
        new_docs.append(doc)

    session.commit()
    return new_docs


def _extract_and_store_entities(
    session: Session,
    documents: list[Document],
    extractor: EntityExtractor,
    embedding_service: EmbeddingService,
) -> int:
    """Run L1 entity extraction on documents and store results.

    Args:
        session: SQLAlchemy sync session.
        documents: List of Document objects to process.
        extractor: EntityExtractor instance.
        embedding_service: EmbeddingService instance.

    Returns:
        Number of entity-document links created.
    """
    link_count = 0

    for doc in documents:
        text = f"{doc.title or ''} {doc.abstract or ''}"
        if not text.strip():
            continue

        extracted = extractor.extract_entities(text)

        for entity_data in extracted:
            entity_name = entity_data.get("name", "").strip()
            if not entity_name or len(entity_name) < 2:
                continue

            canonical = entity_name.lower()
            entity_type = _map_entity_type(entity_data.get("type", "technology"))

            existing_entity = session.execute(
                select(Entity).where(Entity.canonical_name == canonical)
            ).scalar_one_or_none()

            if existing_entity is None:
                embedding = embedding_service.embed_text(canonical)
                entity_obj = Entity(
                    id=uuid.uuid4(),
                    canonical_name=canonical,
                    entity_type=entity_type,
                    aliases=[entity_name] if entity_name != canonical else [],
                    first_seen=datetime.now(timezone.utc),
                    embedding=embedding,
                )
                session.add(entity_obj)
                session.flush()
            else:
                entity_obj = existing_entity

            existing_link = session.execute(
                select(DocumentEntity).where(
                    DocumentEntity.document_id == doc.id,
                    DocumentEntity.entity_id == entity_obj.id,
                )
            ).scalar_one_or_none()

            if existing_link is None:
                doc_entity = DocumentEntity(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    entity_id=entity_obj.id,
                    relevance_score=entity_data.get("confidence", 0.0),
                    extraction_method=ExtractionMethod.L1,
                    raw_mention=entity_name,
                )
                session.add(doc_entity)
                link_count += 1

        doc.processed = True

    session.commit()
    return link_count


def _store_in_neo4j(documents: list[Document], session: Session) -> None:
    """Store document, author, and entity data in Neo4j graph.

    Args:
        documents: List of Document objects.
        session: SQLAlchemy session for querying related entities.
    """
    from app.services.graph.neo4j_service import Neo4jService

    neo4j_svc = Neo4jService(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )

    async def _sync_to_neo4j() -> None:
        await neo4j_svc.ensure_constraints()

        for doc in documents:
            doc_id = str(doc.external_id or doc.id)
            pub_date = doc.published_date.isoformat() if doc.published_date else None

            await neo4j_svc.upsert_paper(
                doc_id=doc_id,
                title=doc.title,
                date=pub_date,
                source=doc.source.value if doc.source else "unknown",
            )

            authors = doc.authors or []
            for author in authors:
                author_name = author.get("name", "")
                if not author_name:
                    continue
                orcid = author.get("orcid", "")
                institution = author.get("institution", "")
                await neo4j_svc.upsert_author(
                    name=author_name, orcid=orcid, institution=institution
                )
                await neo4j_svc.create_relationship(
                    from_id=f"{author_name}|{institution}" if institution else author_name,
                    to_id=doc_id,
                    rel_type="AUTHORED",
                    from_label="Author",
                    to_label="Paper",
                )

            for doc_entity in doc.entities:
                entity = doc_entity.entity
                if entity is None:
                    continue
                await neo4j_svc.upsert_concept(
                    name=entity.canonical_name,
                    entity_type=entity.entity_type.value,
                    embedding=None,
                    aliases=entity.aliases,
                )
                await neo4j_svc.create_relationship(
                    from_id=doc_id,
                    to_id=entity.canonical_name,
                    rel_type="MENTIONS",
                    from_label="Paper",
                    to_label="Concept",
                    properties={"weight": doc_entity.relevance_score or 1.0},
                )

        await neo4j_svc.close()

    try:
        asyncio.run(_sync_to_neo4j())
    except Exception as exc:
        logger.error("Failed to sync to Neo4j: %s", exc)


@celery_app.task(name="app.workers.tasks.ingest_openalex_task", bind=True, max_retries=3)
def ingest_openalex_task(self) -> dict:
    """Fetch recent works from OpenAlex, deduplicate, store, extract entities, embed, and sync to Neo4j."""
    logger.info("Starting OpenAlex ingestion task")

    client = OpenAlexClient()

    try:
        works = asyncio.run(client.fetch_recent_works(
            query="artificial intelligence",
            per_page=50,
            from_date=datetime.now(timezone.utc) - timedelta(days=7),
        ))
    except Exception as exc:
        logger.error("OpenAlex fetch failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
    finally:
        asyncio.run(client.close())

    session = _get_sync_session()
    try:
        new_docs = _store_documents(session, works, DocumentSource.openalex)
        logger.info("Stored %d new documents from OpenAlex (out of %d fetched)", len(new_docs), len(works))

        if new_docs:
            extractor = _get_entity_extractor()
            embedding_service = _get_embedding_service()
            link_count = _extract_and_store_entities(session, new_docs, extractor, embedding_service)
            logger.info("Created %d entity-document links", link_count)

            # Reload docs with entities relationship for Neo4j
            doc_ids = [d.id for d in new_docs]
            loaded_docs = session.execute(
                select(Document).where(Document.id.in_(doc_ids))
            ).scalars().all()
            _store_in_neo4j(list(loaded_docs), session)
    except Exception as exc:
        session.rollback()
        logger.error("OpenAlex ingestion processing failed: %s", exc)
        raise
    finally:
        session.close()

    return {"fetched": len(works), "new_documents": len(new_docs)}


@celery_app.task(name="app.workers.tasks.ingest_arxiv_task", bind=True, max_retries=3)
def ingest_arxiv_task(self) -> dict:
    """Fetch recent papers from arXiv, deduplicate, store, extract entities, embed, and sync to Neo4j."""
    logger.info("Starting arXiv ingestion task")

    client = ArxivClient()

    try:
        papers = asyncio.run(client.fetch_recent_papers(
            category="cs.AI",
            max_results=100,
        ))
    except Exception as exc:
        logger.error("ArXiv fetch failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
    finally:
        asyncio.run(client.close())

    session = _get_sync_session()
    try:
        new_docs = _store_documents(session, papers, DocumentSource.arxiv)
        logger.info("Stored %d new documents from arXiv (out of %d fetched)", len(new_docs), len(papers))

        if new_docs:
            extractor = _get_entity_extractor()
            embedding_service = _get_embedding_service()
            link_count = _extract_and_store_entities(session, new_docs, extractor, embedding_service)
            logger.info("Created %d entity-document links", link_count)

            doc_ids = [d.id for d in new_docs]
            loaded_docs = session.execute(
                select(Document).where(Document.id.in_(doc_ids))
            ).scalars().all()
            _store_in_neo4j(list(loaded_docs), session)
    except Exception as exc:
        session.rollback()
        logger.error("ArXiv ingestion processing failed: %s", exc)
        raise
    finally:
        session.close()

    return {"fetched": len(papers), "new_documents": len(new_docs)}


@celery_app.task(name="app.workers.tasks.detect_novelty_task")
def detect_novelty_task() -> dict:
    """Run novelty detection on recently extracted entities."""
    logger.info("Starting novelty detection task")

    session = _get_sync_session()
    embedding_service = _get_embedding_service()
    novelty_detector = NoveltyDetector()

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_entities = session.execute(
            select(Entity).where(Entity.created_at >= cutoff)
        ).scalars().all()

        all_entities = session.execute(
            select(Entity).where(Entity.created_at < cutoff)
        ).scalars().all()

        existing_entity_dicts = [
            {"name": e.canonical_name, "type": e.entity_type.value}
            for e in all_entities
        ]

        novel_count = 0
        for entity in recent_entities:
            entity_dict = {
                "name": entity.canonical_name,
                "type": entity.entity_type.value,
            }
            novelty_result = novelty_detector.compute_novelty(
                entity_dict, existing_entity_dicts, embedding_service
            )

            if novelty_result.is_novel:
                novel_count += 1
                logger.info(
                    "Novel entity detected: '%s' (score=%.4f)",
                    entity.canonical_name, novelty_result.score,
                )

        logger.info(
            "Novelty detection complete: %d/%d entities are novel",
            novel_count, len(recent_entities),
        )
        return {"total_checked": len(recent_entities), "novel_count": novel_count}
    except Exception as exc:
        logger.error("Novelty detection failed: %s", exc)
        raise
    finally:
        session.close()


@celery_app.task(name="app.workers.tasks.compute_momentum_task")
def compute_momentum_task() -> dict:
    """Compute momentum scores for all active concepts."""
    logger.info("Starting momentum computation task")

    session = _get_sync_session()
    momentum_analyzer = MomentumAnalyzer()

    try:
        entities = session.execute(select(Entity)).scalars().all()
        results: dict[str, float] = {}

        for entity in entities:
            # Build time windows from document associations
            doc_entities = session.execute(
                select(DocumentEntity).where(DocumentEntity.entity_id == entity.id)
            ).scalars().all()

            if not doc_entities:
                continue

            # Group documents by month
            monthly_data: dict[str, dict] = {}
            for de in doc_entities:
                doc = session.execute(
                    select(Document).where(Document.id == de.document_id)
                ).scalar_one_or_none()
                if doc is None or doc.published_date is None:
                    continue

                month_key = doc.published_date.strftime("%Y-%m")
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        "period": month_key,
                        "paper_count": 0,
                        "authors": [],
                        "institutions": [],
                        "countries": [],
                        "citation_count": 0,
                        "betweenness": 0.0,
                        "pagerank": 0.0,
                    }

                monthly_data[month_key]["paper_count"] += 1

                meta = doc.metadata_ or {}
                monthly_data[month_key]["citation_count"] += meta.get("cited_by_count", 0)

                for author in (doc.authors or []):
                    name = author.get("name", "")
                    if name:
                        monthly_data[month_key]["authors"].append(name)
                    inst = author.get("institution", "")
                    if inst:
                        monthly_data[month_key]["institutions"].append(inst)

            if not monthly_data:
                continue

            time_windows = [
                monthly_data[k] for k in sorted(monthly_data.keys())
            ]

            momentum_result = momentum_analyzer.compute_momentum(
                entity.canonical_name, time_windows
            )
            results[entity.canonical_name] = momentum_result.composite_score

        logger.info("Computed momentum for %d concepts", len(results))
        return {"concepts_analyzed": len(results)}
    except Exception as exc:
        logger.error("Momentum computation failed: %s", exc)
        raise
    finally:
        session.close()


@celery_app.task(name="app.workers.tasks.detect_communities_task")
def detect_communities_task() -> dict:
    """Run community detection on the concept graph."""
    logger.info("Starting community detection task")

    from app.services.graph.neo4j_service import Neo4jService
    import json
    import redis as redis_lib

    neo4j_svc = Neo4jService(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )
    community_detector = CommunityDetector()

    try:
        # Fetch concept graph from Neo4j
        async def _fetch_graph() -> dict:
            driver = await neo4j_svc._get_driver()
            if driver is None:
                return {"nodes": [], "edges": []}

            async with driver.session() as neo_session:
                # Get all concepts
                node_result = await neo_session.run(
                    "MATCH (c:Concept) RETURN c.name AS id, c.entity_type AS entity_type"
                )
                nodes = [{"id": r["id"], "entity_type": r["entity_type"]}
                         async for r in node_result if r["id"]]

                # Get all concept-concept relationships (through papers)
                edge_result = await neo_session.run(
                    """
                    MATCH (c1:Concept)<-[:MENTIONS]-(p:Paper)-[:MENTIONS]->(c2:Concept)
                    WHERE c1.name < c2.name
                    WITH c1.name AS source, c2.name AS target, count(p) AS weight
                    RETURN source, target, weight
                    """
                )
                edges = [{"source": r["source"], "target": r["target"], "weight": r["weight"]}
                         async for r in edge_result]

            await neo4j_svc.close()
            return {"nodes": nodes, "edges": edges}

        graph_data = asyncio.run(_fetch_graph())

        if not graph_data["nodes"]:
            logger.info("No concept graph data available for community detection")
            return {"communities": 0, "changes": 0}

        communities = community_detector.detect_communities(graph_data)

        # Load previous communities from Redis for epoch comparison
        redis_client = redis_lib.Redis.from_url(settings.REDIS_URL)
        prev_communities_raw = redis_client.get("weaksignals:communities:latest")
        prev_communities = json.loads(prev_communities_raw) if prev_communities_raw else []

        changes = []
        emerging = []
        if prev_communities:
            changes = community_detector.compare_epochs(communities, prev_communities)
            emerging = community_detector.find_emerging_clusters(changes)

        # Store current communities in Redis for next epoch comparison
        redis_client.set(
            "weaksignals:communities:latest",
            json.dumps(communities),
            ex=86400 * 14,  # expire after 14 days
        )
        redis_client.close()

        logger.info(
            "Community detection complete: %d communities, %d changes, %d emerging",
            len(communities), len(changes), len(emerging),
        )
        return {
            "communities": len(communities),
            "changes": len(changes),
            "emerging": len(emerging),
        }
    except Exception as exc:
        logger.error("Community detection failed: %s", exc)
        raise
    finally:
        asyncio.run(neo4j_svc.close())


@celery_app.task(name="app.workers.tasks.score_signals_task")
def score_signals_task() -> dict:
    """Compute composite scores and create/update Signal records."""
    logger.info("Starting signal scoring task")

    session = _get_sync_session()
    embedding_service = _get_embedding_service()
    novelty_detector = NoveltyDetector()
    momentum_analyzer = MomentumAnalyzer()
    scorer = SignalScorer()

    try:
        # Get all entities with recent activity
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        entities = session.execute(
            select(Entity).where(Entity.created_at >= cutoff)
        ).scalars().all()

        all_entities = session.execute(select(Entity)).scalars().all()
        all_entity_dicts = [
            {"name": e.canonical_name, "type": e.entity_type.value}
            for e in all_entities
        ]

        signals_created = 0
        signals_updated = 0

        for entity in entities:
            entity_dict = {"name": entity.canonical_name, "type": entity.entity_type.value}

            # Compute novelty
            novelty_result = novelty_detector.compute_novelty(
                entity_dict, all_entity_dicts, embedding_service
            )

            # Build time windows for momentum
            doc_entities = session.execute(
                select(DocumentEntity).where(DocumentEntity.entity_id == entity.id)
            ).scalars().all()

            monthly_data: dict[str, dict] = {}
            for de in doc_entities:
                doc = session.execute(
                    select(Document).where(Document.id == de.document_id)
                ).scalar_one_or_none()
                if doc is None or doc.published_date is None:
                    continue

                month_key = doc.published_date.strftime("%Y-%m")
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        "period": month_key,
                        "paper_count": 0,
                        "authors": [],
                        "institutions": [],
                        "countries": [],
                        "citation_count": 0,
                        "betweenness": 0.0,
                        "pagerank": 0.0,
                    }
                monthly_data[month_key]["paper_count"] += 1

            time_windows = [monthly_data[k] for k in sorted(monthly_data.keys())]
            momentum_result = momentum_analyzer.compute_momentum(
                entity.canonical_name, time_windows
            )

            # Use a default community score (would be populated from community detection results)
            community_score = 0.3

            composite = scorer.compute_composite_score(
                novelty=novelty_result.score,
                momentum=momentum_result.composite_score,
                community_change=community_score,
            )

            # Skip noise signals
            if composite.signal_type == "noise":
                continue

            # Map to DB SignalType
            signal_type_map = {
                "emerging_trend": SignalType.emerging_trend,
                "weak_signal": SignalType.weak_signal,
                "strong_signal": SignalType.strong_signal,
            }
            db_signal_type = signal_type_map.get(composite.signal_type, SignalType.emerging_trend)

            # Check for existing signal for this entity
            existing_signal = session.execute(
                select(Signal).where(Signal.title == entity.canonical_name)
            ).scalar_one_or_none()

            if existing_signal is not None:
                existing_signal.novelty_score = novelty_result.score
                existing_signal.momentum_score = momentum_result.composite_score
                existing_signal.composite_score = composite.composite
                existing_signal.signal_type = db_signal_type
                existing_signal.confidence_level = min(
                    novelty_result.score * 0.5 + momentum_result.composite_score * 0.5, 1.0
                )
                signals_updated += 1
            else:
                evidence_doc_ids = [de.document_id for de in doc_entities[:10]]
                signal = Signal(
                    id=uuid.uuid4(),
                    title=entity.canonical_name,
                    description=f"Emerging concept detected: {entity.canonical_name} "
                                f"(type: {entity.entity_type.value})",
                    signal_type=db_signal_type,
                    novelty_score=novelty_result.score,
                    momentum_score=momentum_result.composite_score,
                    composite_score=composite.composite,
                    confidence_level=min(
                        novelty_result.score * 0.5 + momentum_result.composite_score * 0.5, 1.0
                    ),
                    time_horizon="medium",
                    impact_domains=[entity.entity_type.value],
                    evidence_ids=evidence_doc_ids,
                    status=SignalStatus.active,
                )
                session.add(signal)
                signals_created += 1

        session.commit()

        logger.info(
            "Signal scoring complete: %d created, %d updated",
            signals_created, signals_updated,
        )
        return {"signals_created": signals_created, "signals_updated": signals_updated}
    except Exception as exc:
        session.rollback()
        logger.error("Signal scoring failed: %s", exc)
        raise
    finally:
        session.close()


@celery_app.task(name="app.workers.tasks.compute_tenant_relevance_task")
def compute_tenant_relevance_task() -> dict:
    """Compute tenant-specific relevance for all active signals."""
    logger.info("Starting tenant relevance computation task")

    session = _get_sync_session()
    embedding_service = _get_embedding_service()
    scorer = SignalScorer()

    try:
        tenants = session.execute(select(Tenant)).scalars().all()
        active_signals = session.execute(
            select(Signal).where(Signal.status == SignalStatus.active)
        ).scalars().all()

        total_scored = 0

        for tenant in tenants:
            tenant_config = {
                "industry_verticals": tenant.industry_verticals or [],
                "competitor_list": tenant.competitor_list or {},
                "technology_watchlist": tenant.technology_watchlist or [],
                "signal_sensitivity": tenant.signal_sensitivity,
            }

            for signal in active_signals:
                # Build signal data dict
                signal_entities = []
                if signal.evidence_ids:
                    for eid in signal.evidence_ids[:5]:
                        doc = session.execute(
                            select(Document).where(Document.id == eid)
                        ).scalar_one_or_none()
                        if doc:
                            for de in doc.entities:
                                if de.entity:
                                    signal_entities.append(de.entity.canonical_name)

                signal_authors = []
                if signal.evidence_ids:
                    for eid in signal.evidence_ids[:5]:
                        doc = session.execute(
                            select(Document).where(Document.id == eid)
                        ).scalar_one_or_none()
                        if doc and doc.authors:
                            signal_authors.extend(doc.authors)

                signal_data = {
                    "title": signal.title,
                    "description": signal.description or "",
                    "entities": signal_entities,
                    "authors": signal_authors,
                }

                relevance = scorer.compute_tenant_relevance(
                    signal_data, tenant_config, embedding_service
                )

                existing_ts = session.execute(
                    select(TenantSignal).where(
                        TenantSignal.tenant_id == tenant.id,
                        TenantSignal.signal_id == signal.id,
                    )
                ).scalar_one_or_none()

                if existing_ts is not None:
                    existing_ts.relevance_score = relevance.total_relevance
                    existing_ts.industry_relevance = relevance.industry_relevance
                    existing_ts.competitor_activity = relevance.competitor_activity
                    existing_ts.opportunity_score = relevance.opportunity_score
                else:
                    ts = TenantSignal(
                        id=uuid.uuid4(),
                        tenant_id=tenant.id,
                        signal_id=signal.id,
                        relevance_score=relevance.total_relevance,
                        industry_relevance=relevance.industry_relevance,
                        competitor_activity=relevance.competitor_activity,
                        opportunity_score=relevance.opportunity_score,
                    )
                    session.add(ts)

                total_scored += 1

        session.commit()

        logger.info(
            "Tenant relevance complete: scored %d signal-tenant pairs "
            "(%d tenants, %d signals)",
            total_scored, len(tenants), len(active_signals),
        )
        return {
            "tenants": len(tenants),
            "signals": len(active_signals),
            "total_scored": total_scored,
        }
    except Exception as exc:
        session.rollback()
        logger.error("Tenant relevance computation failed: %s", exc)
        raise
    finally:
        session.close()
