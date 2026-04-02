from __future__ import annotations

"""
core/queue/consumer.py

Base consumer loop for the SRS generation worker process.
Updated to support idle timeouts for automatic scale-down.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika import IncomingMessage
from aio_pika.abc import AbstractRobustConnection

from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger

logger = get_logger(__name__)

# Type alias for the async handler the worker must supply
JobHandler = Callable[[str], Awaitable[None]]


def _build_url(settings: Any) -> str:
    return (
        f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}"
        f"@{settings.rabbitmq_host}:{settings.rabbitmq_port}{settings.rabbitmq_vhost}"
    )


async def _process_message(message: IncomingMessage, handler: JobHandler) -> None:
    """
    Decode one message from the queue and call the worker handler.
    """
    async with message.process(ignore_processed=True):
        try:
            body = json.loads(message.body.decode())
            job_id: str = body["job_id"]

            logger.info(f"Consumer | Message received | job_id={job_id}")
            await handler(job_id)
            logger.info(f"Consumer | Job complete | job_id={job_id}")

            await message.ack()

        except KeyError:
            logger.error(
                f"Consumer | Malformed message — missing 'job_id' | "
                f"body={message.body!r}"
            )
            await message.nack(requeue=False)

        except Exception as exc:
            logger.error(
                f"Consumer | Handler raised an exception | "
                f"error={exc}",
                exc_info=True,
            )
            await message.nack(requeue=False)


async def run_consumer(handler: JobHandler, timeout: int | None = None) -> None:
    """
    Connect to RabbitMQ, start consuming from the SRS queue, and block
    until the process receives SIGINT / SIGTERM or the idle timeout is reached.
    """
    settings = get_settings()
    url = _build_url(settings)
    queue_name = settings.rabbitmq_srs_queue

    logger.info(
        f"Consumer | Connecting | "
        f"host={settings.rabbitmq_host} "
        f"port={settings.rabbitmq_port} "
        f"queue={queue_name} "
        f"timeout={timeout}"
    )

    connection: AbstractRobustConnection = await aio_pika.connect_robust(url)

    async with connection:
        channel = await connection.channel()

        # One message at a time per worker process
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(queue_name, durable=True)

        logger.info(f"Consumer | Waiting for jobs | queue={queue_name}")

        # iterator() with timeout will raise asyncio.TimeoutError if idle
        async with queue.iterator(timeout=timeout) as queue_iter:
            try:
                async for message in queue_iter:
                    await _process_message(message, handler)
            except asyncio.TimeoutError:
                logger.info(f"Consumer | Idle timeout reached ({timeout}s) | Exiting gracefully")
                return