from __future__ import annotations

"""
core/queue/publisher.py

Publishes SRS generation job messages to the RabbitMQ queue.

Each message is a small JSON envelope containing only the job_id. The worker
fetches the full job payload from MongoDB using that id, which means the
message queue stays lightweight and the single source of truth for job state
is always the database.

Message envelope:
    {
        "job_id": "<uuid>"
    }
"""

import json

import aio_pika
from aio_pika import DeliveryMode, Message

from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger
from srs_engine.core.queue.rabbitmq import get_rabbitmq_manager

logger = get_logger(__name__)


async def publish_srs_job(job_id: str) -> None:
    """
    Publish a single SRS generation job to the queue.

    Args:
        job_id: The unique identifier of the job record already stored in
                MongoDB. Workers use this to fetch the full payload and
                update progress.

    Raises:
        RuntimeError: If the RabbitMQ channel is not available.
        Exception:    Re-raises any aio_pika publish error after logging.
    """
    settings = get_settings()
    manager = get_rabbitmq_manager()

    if not manager.is_connected:
        raise RuntimeError(
            "Cannot publish SRS job — RabbitMQ is not connected. "
            "Check broker availability and app startup logs."
        )

    payload = json.dumps({"job_id": job_id}).encode()

    message = Message(
        body=payload,
        delivery_mode=DeliveryMode.PERSISTENT,   # survive broker restart
        content_type="application/json",
    )

    queue_name = settings.rabbitmq_srs_queue

    try:
        await manager.channel.default_exchange.publish(
            message,
            routing_key=queue_name,
        )
        logger.info(f"Publisher | Job published | job_id={job_id} | queue={queue_name}")

    except Exception as exc:
        logger.error(
            f"Publisher | Failed to publish job | job_id={job_id} | error={exc}",
            exc_info=True,
        )
        raise