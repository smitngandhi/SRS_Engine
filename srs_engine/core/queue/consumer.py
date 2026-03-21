from __future__ import annotations

"""
core/queue/consumer.py

Base consumer loop for the SRS generation worker process.

This module is intentionally kept separate from the FastAPI app — workers
run as standalone Python processes (e.g. `python -m srs_engine.worker`)
and import only this module plus the services they need.

Usage (inside the worker entry-point):

    import asyncio
    from srs_engine.core.queue.consumer import run_consumer

    async def handle_job(job_id: str) -> None:
        # fetch job from DB, run generation pipeline, update progress
        ...

    asyncio.run(run_consumer(handle_job))
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

    ACK  — sent after the handler returns successfully. RabbitMQ removes
           the message from the queue.
    NACK — sent if the handler raises, with requeue=False so the message
           moves to a dead-letter queue instead of looping forever.
           Change requeue=True here if you want automatic retries.
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


async def run_consumer(handler: JobHandler) -> None:
    """
    Connect to RabbitMQ, start consuming from the SRS queue, and block
    until the process receives SIGINT / SIGTERM.

    Args:
        handler: An async callable ``async def handle(job_id: str) -> None``
                 that the consumer calls for every incoming message.
    """
    settings = get_settings()
    url = _build_url(settings)
    queue_name = settings.rabbitmq_srs_queue

    logger.info(
        f"Consumer | Connecting | "
        f"host={settings.rabbitmq_host} "
        f"port={settings.rabbitmq_port} "
        f"queue={queue_name}"
    )

    connection: AbstractRobustConnection = await aio_pika.connect_robust(url)

    async with connection:
        channel = await connection.channel()

        # One message at a time per worker process — prevents a slow job
        # from starving others when multiple workers share the queue.
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(queue_name, durable=True)

        logger.info(f"Consumer | Waiting for jobs | queue={queue_name}")

        # consume() returns an async iterator; it blocks here until the
        # connection is closed or the process is killed.
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await _process_message(message, handler)