"""
Celery application configuration for Code Review AI
"""
import os
from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "code-review-ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.tasks.analyze_code",
        "workers.tasks.generate_embeddings", 
        "workers.tasks.retrain",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_routes={
        "workers.tasks.analyze_code.*": {"queue": "analysis"},
        "workers.tasks.generate_embeddings.*": {"queue": "embeddings"},
        "workers.tasks.retrain.*": {"queue": "retrain"},
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_exchange_type="direct",
    task_default_routing_key="default",
    result_expires=3600,  # 1 hour
    result_persistent=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Periodic tasks (beat schedule)
celery_app.conf.beat_schedule = {
    "retrain-models": {
        "task": "workers.tasks.retrain.retrain_models",
        "schedule": 604800.0,  # Weekly (7 days)
    },
    "cleanup-old-embeddings": {
        "task": "workers.tasks.generate_embeddings.cleanup_old_embeddings",
        "schedule": 86400.0,  # Daily
    },
    "update-metrics": {
        "task": "workers.tasks.retrain.update_learning_metrics",
        "schedule": 3600.0,  # Hourly
    },
}


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal"""
    print("🚀 Code Review AI worker is ready!")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal"""
    print("👋 Code Review AI worker is shutting down...")


if __name__ == "__main__":
    celery_app.start()
