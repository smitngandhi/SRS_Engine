from __future__ import annotations

"""
core/queue/publisher.py

Publishes SRS generation job messages to the Redis queue.

Each message is simply the job_id string. The worker fetches the full job
payload from MongoDB using that id, which keeps the queue lightweight and
MongoDB as the single source of truth for job state.
"""

from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger
from srs_engine.core.queue.redis_queue import get_redis_manager

logger = get_logger(__name__)


async def publish_srs_job(job_id: str) -> None:
    """
    Publish a single SRS generation job to the Redis queue.

    Args:
        job_id: The unique identifier of the job record already stored in
                MongoDB. Workers use this to fetch the full payload and
                update progress.

    Raises:
        RuntimeError: If the Redis client is not connected.
        Exception:    Re-raises any Redis publish error after logging.
    """
    manager = get_redis_manager()
    settings = get_settings()

    if not manager.is_connected:
        raise RuntimeError(
            "Cannot publish SRS job — Redis is not connected. "
            "Check broker availability and app startup logs."
        )

    try:
        await manager.client.rpush(settings.redis_queue_name, job_id)
        logger.info(f"Publisher | Job published | job_id={job_id} | queue={settings.redis_queue_name}")

    except Exception as exc:
        logger.error(
            f"Publisher | Failed to publish job | job_id={job_id} | error={exc}",
            exc_info=True,
        )
        raise