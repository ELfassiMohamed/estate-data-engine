"""Celery application configuration for distributed scraping."""
from __future__ import annotations

from celery import Celery

from src.config import settings

celery_app = Celery("estate_scraper")

celery_app.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url.rsplit("/", 1)[0] + "/1",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Casablanca",
    enable_utc=True,
    # Reliability: re-queue tasks if a worker crashes mid-execution.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry connection to broker on startup.
    broker_connection_retry_on_startup=True,
)

# Auto-discover tasks defined in src.tasks.
celery_app.autodiscover_tasks(["src"])
