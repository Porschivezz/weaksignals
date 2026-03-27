"""Celery tasks for the Pharmasyntez weak signals pipeline.

Ingests from: PubMed, OpenAlex, ClinicalTrials.gov, arXiv, RSS feeds.
Analyzes with: Google Gemini for signal extraction and scoring.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import redis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.document import Document, DocumentSource
from app.models.entity import DocumentEntity, Entity, EntityType, ExtractionMethod
from app.models.signal import Signal, SignalStatus, SignalType, TenantSignal
from app.models.tenant import Tenant
from app.services.detection.scoring import SignalScorer
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Redis client for progress tracking
_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def _update_progress(task_id: str, data: dict):
    """Update pipeline progress in Redis."""
    r = _get_redis()
    key = f"pipeline_progress:{task_id}"
    r.set(key, json.dumps(data, default=str), ex=3600)  # expire in 1 hour


def get_pipeline_progress(task_id: str) -> dict | None:
    """Read pipeline progress from Redis."""
    r = _get_redis()
    key = f"pipeline_progress:{task_id}"
    raw = r.get(key)
    if raw:
        return json.loads(raw)
    return None

sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
SyncSessionFactory = sessionmaker(bind=sync_engine, expire_on_commit=False)

# Pharmasyntez-specific search queries per cluster
PHARMA_QUERIES = {
    "ai_drug_discovery": [
        "AI drug discovery",
        "machine learning pharmaceutical",
        "self-driving laboratory drug",
        "digital twin clinical trial",
        "generative AI molecule design",
    ],
    "oncology": [
        "CAR-T therapy",
        "antibody drug conjugate ADC",
        "bispecific antibody cancer",
        "mRNA cancer vaccine",
        "chronic myeloid leukemia treatment",
        "PD-1 PD-L1 immunotherapy",
    ],
    "biosimilars": [
        "biosimilar approval",
        "monoclonal antibody biosimilar",
        "patent cliff biologic",
        "биоаналог регистрация Россия",
    ],
    "regulatory": [
        "FDA accelerated approval 2026",
        "EMA PRIME designation",
        "new animal model alternative NAM",
        "ICH guidelines update",
        "Минздрав России регистрация лекарств",
    ],
    "competitors_ru": [
        "Биокад клинические исследования",
        "Генериум препарат",
        "Р-Фарм инновации",
        "Промомед фармацевтика",
        "российский фармрынок 2026",
    ],
    "export_markets": [
        "China biotech licensing deal",
        "EAEU pharmaceutical registration",
        "Russia China pharmaceutical partnership",
        "emerging market pharma expansion",
    ],
}

# PubMed-specific queries (MeSH terms work best)
PUBMED_QUERIES = [
    "(artificial intelligence[MeSH]) AND (drug discovery OR pharmaceutical)",
    "(CAR-T OR chimeric antigen receptor) AND (clinical trial)",
    "(antibody-drug conjugate) AND (cancer)",
    "(biosimilar) AND (monoclonal antibody)",
    "(mRNA vaccine) AND (cancer OR oncology)",
    "(leukemia, myeloid, chronic) AND (treatment)",
    "(diabetes mellitus, type 2) AND (novel therapy OR GLP-1)",
    "(anti-adhesion barrier) AND (surgery)",
    "(HIV) AND (novel compound OR new drug)",
]

# ClinicalTrials.gov queries
CT_QUERIES = [
    "CAR-T therapy cancer",
    "antibody drug conjugate",
    "biosimilar monoclonal antibody",
    "mRNA cancer vaccine",
    "chronic myeloid leukemia",
    "type 2 diabetes novel",
    "adhesion prevention surgery",
]

# arXiv categories for pharma-relevant AI
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "q-bio.QM"]


def _get_sync_session() -> Session:
    return SyncSessionFactory()


def _store_documents(session: Session, works: list[dict], source: DocumentSource) -> list[Document]:
    """Store normalized works as Document records, deduplicating by external_id."""
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

        # Map source string to enum
        source_map = {
            "pubmed": DocumentSource.pubmed,
            "openalex": DocumentSource.openalex,
            "arxiv": DocumentSource.arxiv,
            "clinicaltrials": DocumentSource.clinicaltrials,
            "rss": DocumentSource.rss,
        }
        doc_source = source_map.get(work.get("source", ""), source)

        doc = Document(
            id=uuid.uuid4(),
            external_id=external_id,
            source=doc_source,
            title=work.get("title", ""),
            abstract=work.get("abstract", ""),
            authors=work.get("authors"),
            published_date=work.get("published_date"),
            metadata_={
                "concepts": work.get("concepts", []),
                "cited_by_count": work.get("cited_by_count", 0),
                "doi": work.get("doi", ""),
                **(work.get("metadata_extra", {})),
            },
            processed=False,
        )
        session.add(doc)
        new_docs.append(doc)

    if new_docs:
        session.commit()
    return new_docs

@celery_app.task(name="app.workers.tasks.ingest_all_sources_task", bind=True, max_retries=2)
def ingest_all_sources_task(self) -> dict:
    """Ingest from all data sources: PubMed, OpenAlex, ClinicalTrials.gov, arXiv, RSS."""
    logger.info("=== Starting full ingestion pipeline ===")
    results = {"pubmed": 0, "openalex": 0, "clinicaltrials": 0, "arxiv": 0, "rss": 0}
    session = _get_sync_session()

    try:
        # 1. PubMed
        try:
            from app.services.ingestion.pubmed import PubMedClient
            async def fetch_pubmed():
                client = PubMedClient(email=settings.PUBMED_EMAIL)
                try:
                    docs = []
                    for query in PUBMED_QUERIES:
                        docs.extend(await client.search_and_fetch(query, max_results=20, days_back=30))
                    return docs
                finally:
                    await client.close()

            all_pubmed = asyncio.run(fetch_pubmed())
            new_docs = _store_documents(session, all_pubmed, DocumentSource.pubmed)
            results["pubmed"] = len(new_docs)
            logger.info("PubMed: %d new documents (from %d fetched)", len(new_docs), len(all_pubmed))
        except Exception as exc:
            logger.error("PubMed ingestion failed: %s", exc)

        # 2. OpenAlex
        try:
            from app.services.ingestion.openalex import OpenAlexClient
            async def fetch_openalex():
                client = OpenAlexClient(email=settings.OPENALEX_EMAIL)
                try:
                    docs = []
                    openalex_queries = [
                        "AI drug discovery pharmaceutical",
                        "biosimilar monoclonal antibody",
                        "CAR-T immunotherapy",
                        "mRNA cancer vaccine",
                        "antibody drug conjugate",
                    ]
                    for query in openalex_queries:
                        docs.extend(await client.fetch_recent_works(
                            query=query, per_page=25,
                            from_date=datetime.now(timezone.utc) - timedelta(days=30),
                            max_pages=2,
                        ))
                    return docs
                finally:
                    await client.close()

            all_openalex = asyncio.run(fetch_openalex())
            new_docs = _store_documents(session, all_openalex, DocumentSource.openalex)
            results["openalex"] = len(new_docs)
            logger.info("OpenAlex: %d new documents (from %d fetched)", len(new_docs), len(all_openalex))
        except Exception as exc:
            logger.error("OpenAlex ingestion failed: %s", exc)

        # 3. ClinicalTrials.gov
        try:
            from app.services.ingestion.clinicaltrials import ClinicalTrialsClient
            async def fetch_ct():
                client = ClinicalTrialsClient()
                try:
                    docs = []
                    for query in CT_QUERIES:
                        docs.extend(await client.search_studies(query, max_results=15, days_back=60))
                    return docs
                finally:
                    await client.close()

            all_ct = asyncio.run(fetch_ct())
            new_docs = _store_documents(session, all_ct, DocumentSource.clinicaltrials)
            results["clinicaltrials"] = len(new_docs)
            logger.info("ClinicalTrials: %d new documents (from %d fetched)", len(new_docs), len(all_ct))
        except Exception as exc:
            logger.error("ClinicalTrials ingestion failed: %s", exc)

        # 4. arXiv
        try:
            from app.services.ingestion.arxiv import ArxivClient
            async def fetch_arxiv():
                client = ArxivClient()
                try:
                    docs = []
                    for cat in ARXIV_CATEGORIES:
                        docs.extend(await client.fetch_recent_papers(category=cat, max_results=30))
                    return docs
                finally:
                    await client.close()

            all_arxiv = asyncio.run(fetch_arxiv())
            new_docs = _store_documents(session, all_arxiv, DocumentSource.arxiv)
            results["arxiv"] = len(new_docs)
            logger.info("arXiv: %d new documents (from %d fetched)", len(new_docs), len(all_arxiv))
        except Exception as exc:
            logger.error("arXiv ingestion failed: %s", exc)

        # 5. RSS Feeds
        try:
            from app.services.ingestion.rss_feeds import RSSFeedClient
            async def fetch_rss():
                client = RSSFeedClient()
                try:
                    return await client.fetch_all_feeds()
                finally:
                    await client.close()

            all_rss = asyncio.run(fetch_rss())
            new_docs = _store_documents(session, all_rss, DocumentSource.rss)
            results["rss"] = len(new_docs)
            logger.info("RSS: %d new documents (from %d fetched)", len(new_docs), len(all_rss))
        except Exception as exc:
            logger.error("RSS ingestion failed: %s", exc)

    except Exception as exc:
        session.rollback()
        logger.error("Full ingestion failed: %s", exc)
        raise
    finally:
        session.close()

    total = sum(results.values())
    logger.info("=== Ingestion complete: %d total new documents ===", total)
    return results


@celery_app.task(name="app.workers.tasks.analyze_and_score_task", bind=True, max_retries=2)
def analyze_and_score_task(self) -> dict:
    """Analyze unprocessed documents with Gemini and create/update signals."""
    logger.info("=== Starting analysis and scoring pipeline ===")

    if not settings.GEMINI_API_KEY and not settings.OPENROUTER_API_KEY:
        logger.warning("No LLM API key set (GEMINI_API_KEY or OPENROUTER_API_KEY), skipping analysis")
        return {"error": "No LLM API key configured"}

    session = _get_sync_session()

    try:
        # Get unprocessed documents
        unprocessed = session.execute(
            select(Document)
            .where(Document.processed == False)
            .order_by(Document.ingested_at.desc())
            .limit(100)
        ).scalars().all()

        if not unprocessed:
            logger.info("No unprocessed documents to analyze")
            return {"analyzed": 0, "signals_created": 0}

        logger.info("Analyzing %d unprocessed documents", len(unprocessed))

        from app.services.nlp.gemini_analyzer import GeminiAnalyzer

        async def process_analysis(docs_list):
            analyzer = GeminiAnalyzer(
                api_key=settings.GEMINI_API_KEY,
                openrouter_api_key=settings.OPENROUTER_API_KEY,
                openrouter_model=settings.OPENROUTER_MODEL,
            )
            try:
                all_sig = []
                batch_size = 15
                for i in range(0, len(docs_list), batch_size):
                    batch = docs_list[i:i + batch_size]
                    batch_ids = [str(d.id) for d in batch]
                    doc_dicts = [
                        {
                            "title": d.title,
                            "abstract": d.abstract or "",
                            "source": d.source.value if d.source else "unknown",
                        }
                        for d in batch
                    ]
                    try:
                        signals = await analyzer.analyze_documents(doc_dicts)
                        # Map source_doc_indices to actual document UUIDs
                        for sig in signals:
                            indices = sig.get("source_doc_indices", [])
                            doc_uuids = []
                            for idx in indices:
                                if isinstance(idx, int) and 0 <= idx < len(batch_ids):
                                    doc_uuids.append(batch_ids[idx])
                            sig["_evidence_ids"] = doc_uuids
                        all_sig.extend(signals)
                    except Exception as exc:
                        logger.error("Gemini analysis failed for batch %d: %s", i, exc)
                return all_sig
            finally:
                await analyzer.close()

        # Run analysis entirely in one loop
        all_signals = asyncio.run(process_analysis(unprocessed))

        # Mark as processed
        for doc in unprocessed:
            doc.processed = True
        session.commit()

        # Create/update Signal records
        signals_created = 0
        signals_updated = 0
        scorer = SignalScorer()

        for sig_data in all_signals:
            title = sig_data.get("title_ru", sig_data.get("title_en", ""))
            if not title:
                continue

            description = sig_data.get("description_ru", "")
            cluster = sig_data.get("cluster", "")
            novelty = float(sig_data.get("novelty_score", 0.5))
            momentum = float(sig_data.get("momentum_score", 0.5))
            relevance = float(sig_data.get("relevance_to_pharmasyntez", 0.5))

            # Map signal type
            sig_type_str = sig_data.get("signal_type", "emerging_trend")
            sig_type_map = {
                "weak_signal": SignalType.weak_signal,
                "emerging_trend": SignalType.emerging_trend,
                "strong_signal": SignalType.strong_signal,
            }
            sig_type = sig_type_map.get(sig_type_str, SignalType.emerging_trend)

            composite = scorer.compute_composite_score(novelty, momentum, 0.3)

            # Check for existing signal with same title
            existing = session.execute(
                select(Signal).where(Signal.title == title)
            ).scalar_one_or_none()

            # Get evidence document UUIDs from batch mapping
            evidence_uuids = sig_data.get("_evidence_ids", [])

            if existing:
                existing.novelty_score = max(existing.novelty_score, novelty)
                existing.momentum_score = max(existing.momentum_score, momentum)
                existing.composite_score = composite.composite
                existing.last_updated = datetime.now(timezone.utc)
                # Append new evidence_ids to existing ones
                old_ids = existing.evidence_ids or []
                merged = list(set(str(x) for x in old_ids) | set(evidence_uuids))
                existing.evidence_ids = [uuid.UUID(x) for x in merged] if merged else None
                signals_updated += 1
            else:
                signal = Signal(
                    id=uuid.uuid4(),
                    title=title,
                    description=description,
                    cluster=cluster,
                    signal_type=sig_type,
                    novelty_score=novelty,
                    momentum_score=momentum,
                    composite_score=composite.composite,
                    confidence_level=relevance,
                    time_horizon=sig_data.get("time_horizon", "medium"),
                    impact_domains=sig_data.get("impact_domains", []),
                    evidence_ids=[uuid.UUID(x) for x in evidence_uuids] if evidence_uuids else None,
                    status=SignalStatus.active,
                )
                session.add(signal)
                signals_created += 1

                # Create entities from signal
                for entity_name in sig_data.get("entities", []):
                    if not entity_name or len(entity_name) < 2:
                        continue
                    canonical = entity_name.lower().strip()
                    existing_entity = session.execute(
                        select(Entity).where(Entity.canonical_name == canonical)
                    ).scalar_one_or_none()

                    if not existing_entity:
                        entity = Entity(
                            id=uuid.uuid4(),
                            canonical_name=canonical,
                            entity_type=EntityType.technology,
                            aliases=[entity_name] if entity_name != canonical else [],
                            first_seen=datetime.now(timezone.utc),
                        )
                        session.add(entity)

        session.commit()

        logger.info(
            "=== Analysis complete: %d signals created, %d updated ===",
            signals_created, signals_updated,
        )
        return {
            "analyzed": len(unprocessed),
            "signals_created": signals_created,
            "signals_updated": signals_updated,
        }
    except Exception as exc:
        session.rollback()
        logger.error("Analysis and scoring failed: %s", exc)
        raise
    finally:
        session.close()

@celery_app.task(name="app.workers.tasks.compute_tenant_relevance_task")
def compute_tenant_relevance_task() -> dict:
    """Compute tenant-specific relevance for all active signals."""
    logger.info("Starting tenant relevance computation")

    session = _get_sync_session()
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
                signal_data = {
                    "title": signal.title,
                    "description": signal.description or "",
                    "entities": [],
                    "authors": [],
                }

                relevance = scorer.compute_tenant_relevance(signal_data, tenant_config)

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
        logger.info("Tenant relevance: scored %d pairs", total_scored)
        return {"tenants": len(tenants), "signals": len(active_signals), "total_scored": total_scored}
    except Exception as exc:
        session.rollback()
        logger.error("Tenant relevance failed: %s", exc)
        raise
    finally:
        session.close()


@celery_app.task(name="app.workers.tasks.run_initial_ingestion_task")
def run_initial_ingestion_task() -> dict:
    """One-time task to populate the database with initial data."""
    logger.info("=== Running initial data population ===")
    result1 = ingest_all_sources_task()
    result2 = analyze_and_score_task()
    result3 = compute_tenant_relevance_task()
    return {"ingestion": result1, "analysis": result2, "relevance": result3}


@celery_app.task(name="app.workers.tasks.run_full_pipeline_task", bind=True, max_retries=1)
def run_full_pipeline_task(self) -> dict:
    """Run the full pipeline (ingestion → analysis → relevance) with progress tracking."""
    task_id = self.request.id
    logger.info("=== Starting full pipeline with progress tracking (task_id=%s) ===", task_id)

    progress = {
        "task_id": task_id,
        "status": "running",
        "stage": "ingestion",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "error": None,
        "ingestion": {
            "status": "running",
            "sources": {"pubmed": 0, "openalex": 0, "clinicaltrials": 0, "arxiv": 0, "rss": 0},
            "total_fetched": {"pubmed": 0, "openalex": 0, "clinicaltrials": 0, "arxiv": 0, "rss": 0},
            "total_new": 0,
            "current_source": "pubmed",
        },
        "analysis": {
            "status": "pending",
            "total_docs": 0,
            "analyzed": 0,
            "signals_created": 0,
            "signals_updated": 0,
        },
        "relevance": {
            "status": "pending",
            "scored": 0,
        },
    }
    _update_progress(task_id, progress)

    session = _get_sync_session()

    try:
        # ============ STAGE 1: INGESTION ============
        # PubMed
        progress["ingestion"]["current_source"] = "PubMed"
        _update_progress(task_id, progress)
        try:
            from app.services.ingestion.pubmed import PubMedClient
            async def fetch_pubmed():
                client = PubMedClient(email=settings.PUBMED_EMAIL)
                try:
                    docs = []
                    for query in PUBMED_QUERIES:
                        docs.extend(await client.search_and_fetch(query, max_results=20, days_back=30))
                    return docs
                finally:
                    await client.close()
            all_pubmed = asyncio.run(fetch_pubmed())
            progress["ingestion"]["total_fetched"]["pubmed"] = len(all_pubmed)
            new_docs = _store_documents(session, all_pubmed, DocumentSource.pubmed)
            progress["ingestion"]["sources"]["pubmed"] = len(new_docs)
            progress["ingestion"]["total_new"] += len(new_docs)
            _update_progress(task_id, progress)
            logger.info("PubMed: %d new documents (from %d fetched)", len(new_docs), len(all_pubmed))
        except Exception as exc:
            logger.error("PubMed ingestion failed: %s", exc)

        # OpenAlex
        progress["ingestion"]["current_source"] = "OpenAlex"
        _update_progress(task_id, progress)
        try:
            from app.services.ingestion.openalex import OpenAlexClient
            async def fetch_openalex():
                client = OpenAlexClient(email=settings.OPENALEX_EMAIL)
                try:
                    docs = []
                    openalex_queries = [
                        "AI drug discovery pharmaceutical",
                        "biosimilar monoclonal antibody",
                        "CAR-T immunotherapy",
                        "mRNA cancer vaccine",
                        "antibody drug conjugate",
                    ]
                    for query in openalex_queries:
                        docs.extend(await client.fetch_recent_works(
                            query=query, per_page=25,
                            from_date=datetime.now(timezone.utc) - timedelta(days=30),
                            max_pages=2,
                        ))
                    return docs
                finally:
                    await client.close()
            all_openalex = asyncio.run(fetch_openalex())
            progress["ingestion"]["total_fetched"]["openalex"] = len(all_openalex)
            new_docs = _store_documents(session, all_openalex, DocumentSource.openalex)
            progress["ingestion"]["sources"]["openalex"] = len(new_docs)
            progress["ingestion"]["total_new"] += len(new_docs)
            _update_progress(task_id, progress)
            logger.info("OpenAlex: %d new documents (from %d fetched)", len(new_docs), len(all_openalex))
        except Exception as exc:
            logger.error("OpenAlex ingestion failed: %s", exc)

        # ClinicalTrials
        progress["ingestion"]["current_source"] = "ClinicalTrials.gov"
        _update_progress(task_id, progress)
        try:
            from app.services.ingestion.clinicaltrials import ClinicalTrialsClient
            async def fetch_ct():
                client = ClinicalTrialsClient()
                try:
                    docs = []
                    for query in CT_QUERIES:
                        docs.extend(await client.search_studies(query, max_results=15, days_back=60))
                    return docs
                finally:
                    await client.close()
            all_ct = asyncio.run(fetch_ct())
            progress["ingestion"]["total_fetched"]["clinicaltrials"] = len(all_ct)
            new_docs = _store_documents(session, all_ct, DocumentSource.clinicaltrials)
            progress["ingestion"]["sources"]["clinicaltrials"] = len(new_docs)
            progress["ingestion"]["total_new"] += len(new_docs)
            _update_progress(task_id, progress)
            logger.info("ClinicalTrials: %d new documents (from %d fetched)", len(new_docs), len(all_ct))
        except Exception as exc:
            logger.error("ClinicalTrials ingestion failed: %s", exc)

        # arXiv
        progress["ingestion"]["current_source"] = "arXiv"
        _update_progress(task_id, progress)
        try:
            from app.services.ingestion.arxiv import ArxivClient
            async def fetch_arxiv():
                client = ArxivClient()
                try:
                    docs = []
                    for cat in ARXIV_CATEGORIES:
                        docs.extend(await client.fetch_recent_papers(category=cat, max_results=30))
                    return docs
                finally:
                    await client.close()
            all_arxiv = asyncio.run(fetch_arxiv())
            progress["ingestion"]["total_fetched"]["arxiv"] = len(all_arxiv)
            new_docs = _store_documents(session, all_arxiv, DocumentSource.arxiv)
            progress["ingestion"]["sources"]["arxiv"] = len(new_docs)
            progress["ingestion"]["total_new"] += len(new_docs)
            _update_progress(task_id, progress)
            logger.info("arXiv: %d new documents (from %d fetched)", len(new_docs), len(all_arxiv))
        except Exception as exc:
            logger.error("arXiv ingestion failed: %s", exc)

        # RSS
        progress["ingestion"]["current_source"] = "RSS-ленты"
        _update_progress(task_id, progress)
        try:
            from app.services.ingestion.rss_feeds import RSSFeedClient
            async def fetch_rss():
                client = RSSFeedClient()
                try:
                    return await client.fetch_all_feeds()
                finally:
                    await client.close()
            all_rss = asyncio.run(fetch_rss())
            progress["ingestion"]["total_fetched"]["rss"] = len(all_rss)
            new_docs = _store_documents(session, all_rss, DocumentSource.rss)
            progress["ingestion"]["sources"]["rss"] = len(new_docs)
            progress["ingestion"]["total_new"] += len(new_docs)
            _update_progress(task_id, progress)
            logger.info("RSS: %d new documents (from %d fetched)", len(new_docs), len(all_rss))
        except Exception as exc:
            logger.error("RSS ingestion failed: %s", exc)

        progress["ingestion"]["status"] = "completed"
        progress["ingestion"]["current_source"] = None

        # ============ STAGE 2: ANALYSIS ============
        progress["stage"] = "analysis"
        progress["analysis"]["status"] = "running"
        _update_progress(task_id, progress)

        if not settings.GEMINI_API_KEY and not settings.OPENROUTER_API_KEY:
            logger.warning("No LLM API key configured, skipping analysis")
            progress["analysis"]["status"] = "skipped"
            progress["analysis"]["error"] = "Нет API-ключа LLM"
        else:
            unprocessed = session.execute(
                select(Document)
                .where(Document.processed == False)
                .order_by(Document.ingested_at.desc())
                .limit(100)
            ).scalars().all()

            progress["analysis"]["total_docs"] = len(unprocessed)
            _update_progress(task_id, progress)

            if unprocessed:
                from app.services.nlp.gemini_analyzer import GeminiAnalyzer

                async def process_analysis_tracked(docs_list):
                    analyzer = GeminiAnalyzer(
                        api_key=settings.GEMINI_API_KEY,
                        openrouter_api_key=settings.OPENROUTER_API_KEY,
                        openrouter_model=settings.OPENROUTER_MODEL,
                    )
                    try:
                        all_sig = []
                        batch_size = 15
                        for i in range(0, len(docs_list), batch_size):
                            batch = docs_list[i:i + batch_size]
                            batch_ids = [str(d.id) for d in batch]
                            doc_dicts = [
                                {
                                    "title": d.title,
                                    "abstract": d.abstract or "",
                                    "source": d.source.value if d.source else "unknown",
                                }
                                for d in batch
                            ]
                            try:
                                signals = await analyzer.analyze_documents(doc_dicts)
                                for sig in signals:
                                    indices = sig.get("source_doc_indices", [])
                                    doc_uuids = []
                                    for idx in indices:
                                        if isinstance(idx, int) and 0 <= idx < len(batch_ids):
                                            doc_uuids.append(batch_ids[idx])
                                    sig["_evidence_ids"] = doc_uuids
                                all_sig.extend(signals)
                            except Exception as exc:
                                logger.error("LLM analysis failed for batch %d: %s", i, exc)

                            # Update progress after each batch
                            progress["analysis"]["analyzed"] = min(i + batch_size, len(docs_list))
                            progress["analysis"]["signals_created"] = len(all_sig)
                            _update_progress(task_id, progress)

                        return all_sig
                    finally:
                        await analyzer.close()

                all_signals = asyncio.run(process_analysis_tracked(unprocessed))

                # Mark as processed
                for doc in unprocessed:
                    doc.processed = True
                session.commit()

                # Create/update Signal records
                signals_created = 0
                signals_updated = 0
                scorer = SignalScorer()

                for sig_data in all_signals:
                    title = sig_data.get("title_ru", sig_data.get("title_en", ""))
                    if not title:
                        continue

                    description = sig_data.get("description_ru", "")
                    cluster = sig_data.get("cluster", "")
                    novelty = float(sig_data.get("novelty_score", 0.5))
                    momentum = float(sig_data.get("momentum_score", 0.5))
                    relevance = float(sig_data.get("relevance_to_pharmasyntez", 0.5))

                    sig_type_str = sig_data.get("signal_type", "emerging_trend")
                    sig_type_map = {
                        "weak_signal": SignalType.weak_signal,
                        "emerging_trend": SignalType.emerging_trend,
                        "strong_signal": SignalType.strong_signal,
                    }
                    sig_type = sig_type_map.get(sig_type_str, SignalType.emerging_trend)
                    composite = scorer.compute_composite_score(novelty, momentum, 0.3)

                    existing = session.execute(
                        select(Signal).where(Signal.title == title)
                    ).scalar_one_or_none()

                    evidence_uuids = sig_data.get("_evidence_ids", [])

                    if existing:
                        existing.novelty_score = max(existing.novelty_score, novelty)
                        existing.momentum_score = max(existing.momentum_score, momentum)
                        existing.composite_score = composite.composite
                        existing.last_updated = datetime.now(timezone.utc)
                        old_ids = existing.evidence_ids or []
                        merged = list(set(str(x) for x in old_ids) | set(evidence_uuids))
                        existing.evidence_ids = [uuid.UUID(x) for x in merged] if merged else None
                        signals_updated += 1
                    else:
                        signal_obj = Signal(
                            id=uuid.uuid4(),
                            title=title,
                            description=description,
                            cluster=cluster,
                            signal_type=sig_type,
                            novelty_score=novelty,
                            momentum_score=momentum,
                            composite_score=composite.composite,
                            confidence_level=relevance,
                            time_horizon=sig_data.get("time_horizon", "medium"),
                            impact_domains=sig_data.get("impact_domains", []),
                            evidence_ids=[uuid.UUID(x) for x in evidence_uuids] if evidence_uuids else None,
                            status=SignalStatus.active,
                        )
                        session.add(signal_obj)
                        signals_created += 1

                        for entity_name in sig_data.get("entities", []):
                            if not entity_name or len(entity_name) < 2:
                                continue
                            canonical = entity_name.lower().strip()
                            existing_entity = session.execute(
                                select(Entity).where(Entity.canonical_name == canonical)
                            ).scalar_one_or_none()
                            if not existing_entity:
                                entity = Entity(
                                    id=uuid.uuid4(),
                                    canonical_name=canonical,
                                    entity_type=EntityType.technology,
                                    aliases=[entity_name] if entity_name != canonical else [],
                                    first_seen=datetime.now(timezone.utc),
                                )
                                session.add(entity)

                session.commit()
                progress["analysis"]["signals_created"] = signals_created
                progress["analysis"]["signals_updated"] = signals_updated
            else:
                logger.info("No unprocessed documents to analyze")

            progress["analysis"]["status"] = "completed"

        # ============ STAGE 3: TENANT RELEVANCE ============
        progress["stage"] = "relevance"
        progress["relevance"]["status"] = "running"
        _update_progress(task_id, progress)

        scorer = SignalScorer()
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
                signal_data = {
                    "title": signal.title,
                    "description": signal.description or "",
                    "entities": [],
                    "authors": [],
                }
                relevance = scorer.compute_tenant_relevance(signal_data, tenant_config)
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
        progress["relevance"]["scored"] = total_scored
        progress["relevance"]["status"] = "completed"

        # ============ DONE ============
        progress["stage"] = "done"
        progress["status"] = "completed"
        progress["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_progress(task_id, progress)

        logger.info("=== Full pipeline complete: %d new docs, %d signals created, %d updated, %d scored ===",
                     progress["ingestion"]["total_new"],
                     progress["analysis"]["signals_created"],
                     progress["analysis"]["signals_updated"],
                     total_scored)

        return progress

    except Exception as exc:
        session.rollback()
        progress["status"] = "failed"
        progress["error"] = str(exc)
        progress["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_progress(task_id, progress)
        logger.error("Full pipeline failed: %s", exc)
        raise
    finally:
        session.close()
