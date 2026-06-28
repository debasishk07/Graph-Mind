from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "graphmind",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.parse_worker", "app.workers.embedding_worker", "app.workers.analysis_worker", "app.workers.maintenance_worker"],
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 min soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    result_expires=86400,  # 24 hours
    beat_schedule={
        "cleanup-old-tasks": {
            "task": "app.workers.maintenance.cleanup_old_tasks",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        },
    },
)

# Task routes
celery_app.conf.task_routes = {
    "app.workers.parse_worker.parse_repository_task": {"queue": "parsing"},
    "app.workers.embedding_worker.generate_embeddings_task": {"queue": "embeddings"},
    "app.workers.analysis_worker.analyze_repository_task": {"queue": "analysis"},
}

if __name__ == "__main__":
    celery_app.start()