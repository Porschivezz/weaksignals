"""Celery application configuration with Redis broker and periodic beat schedule."""

import logging

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "weaksignals",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=1800,
    task_time_limit=3600,
    result_expires=86400,
)

celery_app.conf.beat_schedule = {
    "ingest-openalex": {
        "task": "app.workers.tasks.ingest_openalex_task",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": (),
        "options": {"queue": "ingestion"},
    },
    "ingest-arxiv": {
        "task": "app.workers.tasks.ingest_arxiv_task",
        "schedule": crontab(minute=0, hour="*/4"),
        "args": (),
        "options": {"queue": "ingestion"},
    },
    "detect-novelty": {
        "task": "app.workers.tasks.detect_novelty_task",
        "schedule": crontab(minute=0, hour=2),
        "args": (),
        "options": {"queue": "detection"},
    },
    "compute-momentum": {
        "task": "app.workers.tasks.compute_momentum_task",
        "schedule": crontab(minute=0, hour=3, day_of_week=1),
        "args": (),
        "options": {"queue": "detection"},
    },
    "detect-communities": {
        "task": "app.workers.tasks.detect_communities_task",
        "schedule": crontab(minute=0, hour=4, day_of_week=1),
        "args": (),
        "options": {"queue": "detection"},
    },
    "score-signals": {
        "task": "app.workers.tasks.score_signals_task",
        "schedule": crontab(minute=0, hour=5, day_of_week=1),
        "args": (),
        "options": {"queue": "detection"},
    },
    "compute-tenant-relevance": {
        "task": "app.workers.tasks.compute_tenant_relevance_task",
        "schedule": crontab(minute=0, hour=6, day_of_week=1),
        "args": (),
        "options": {"queue": "detection"},
    },
}
