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
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "ingest-all-sources": {
        "task": "app.workers.tasks.ingest_all_sources_task",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "analyze-and-score": {
        "task": "app.workers.tasks.analyze_and_score_task",
        "schedule": crontab(minute=30, hour="*/6"),
    },
    "compute-tenant-relevance": {
        "task": "app.workers.tasks.compute_tenant_relevance_task",
        "schedule": crontab(minute=0, hour=3),
    },
}
