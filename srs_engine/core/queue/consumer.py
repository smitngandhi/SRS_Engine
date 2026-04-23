from __future__ import annotations

"""
core/queue/consumer.py

Base consumer loop for the SRS generation worker process.
Uses RPOPLPUSH reliable queue pattern — jobs are atomically moved from the
main queue to a processing queue, then removed on success or requeued on
failure. This ensures no job is lost if the worker crashes mid-execution.
"""

import asyncio
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis

from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger
from srs_engine.core.queue.redis_queue import get_redis_manager

logger = get_logger(__name__)

# Type alias for the async handler the worker must supply
JobHandler = Callable[[str], Awaitable[None]]

# Name of the in-flight queue (jobs move here while being processed)
PROCESSING_QUEUE = "srs_processing"


async def run_consumer(handler: JobHandler, timeout: int | None = None) -> None:
    """
    Connect to Redis and block-pop jobs from the SRS queue one at a time,
    calling handler(job_id) for each job.

    Uses BRPOPLPUSH to atomically move each job from the main queue into a
    processing queue before calling the handler. On success, the job is
    removed from the processing queue. On failure, it is moved back to the
    main queue for retry.

    Args:
        handler: Async callable that processes a single job_id.
        timeout: Seconds to wait for a job before returning (0 = block forever).
                 None is treated as 0 (block forever).
    """
    settings = get_settings()
    manager = get_redis_manager()
    
    # Ensure we are connected
    if not manager.is_connected:
        await manager.connect()
    
    client = manager.client
    queue = settings.redis_queue_name
    pop_timeout = timeout or 0

    logger.info(
        f"Consumer | Connected | "
        f"url={settings.redis_url} "
        f"queue={queue} "
        f"timeout={pop_timeout}"
    )

    try:
        while True:
            # Atomically move job from main queue → processing queue
            # Note: client is from redis_queue.py which handles SSL/TLS correctly
            raw = await client.brpoplpush(queue, PROCESSING_QUEUE, timeout=pop_timeout)

            if raw is None:
                # Timeout reached — exit gracefully
                logger.info(f"Consumer | Idle timeout reached ({pop_timeout}s) | Exiting gracefully")
                break

            job_id = raw.decode() if isinstance(raw, bytes) else raw
            logger.info(f"Consumer | Message received | job_id={job_id}")

            try:
                await handler(job_id)
                # Success: remove from processing queue
                await client.lrem(PROCESSING_QUEUE, 1, job_id)
                logger.info(f"Consumer | Job complete | job_id={job_id}")

            except Exception as exc:
                logger.error(
                    f"Consumer | Handler raised an exception | job_id={job_id} | error={exc}",
                    exc_info=True,
                )
                # Move failed job back to main queue for retry
                await client.lrem(PROCESSING_QUEUE, 1, job_id)
                await client.lpush(queue, job_id)
                raise

    finally:
        # We don't close the manager's client here as it's shared
        pass