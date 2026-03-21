from __future__ import annotations

"""
core/queue/rabbitmq.py

Manages a single persistent async RabbitMQ connection and channel for the
FastAPI process. The connection is opened during app lifespan startup and
closed on shutdown. Both the publisher and the SSE endpoint use this shared
channel — workers run in a separate process and create their own connection
via connect().
"""

import asyncio
from typing import Optional

import aio_pika
from aio_pika import Connection, Channel, ExchangeType
from aio_pika.abc import AbstractRobustConnection

from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger

logger = get_logger(__name__)


class RabbitMQManager:
    """
    Holds a single robust connection + channel for the lifetime of the
    FastAPI application process.

    A RobustConnection automatically reconnects after transient failures
    (e.g. broker restart) without any extra code on our side.
    """

    def __init__(self) -> None:
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[Channel] = None
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self) -> str:
        s = self._settings
        return (
            f"amqp://{s.rabbitmq_user}:{s.rabbitmq_password}"
            f"@{s.rabbitmq_host}:{s.rabbitmq_port}{s.rabbitmq_vhost}"
        )

    async def _declare_queue(self, channel: Channel) -> None:
        """
        Declare the SRS generation queue as durable so messages survive a
        broker restart. Idempotent — safe to call multiple times.
        """
        queue_name = self._settings.rabbitmq_srs_queue
        await channel.declare_queue(queue_name, durable=True)
        logger.info(f"RabbitMQ | Queue declared | queue={queue_name}")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Open a robust connection and a single channel, then declare the
        target queue. Called once during app lifespan startup.
        """
        url = self._build_url()
        logger.info(
            f"RabbitMQ | Connecting | "
            f"host={self._settings.rabbitmq_host} "
            f"port={self._settings.rabbitmq_port}"
        )

        self._connection = await aio_pika.connect_robust(url)
        self._channel = await self._connection.channel()

        # Limit the worker-side prefetch so a single worker doesn't hoard
        # all jobs when multiple workers are running.
        await self._channel.set_qos(prefetch_count=1)

        await self._declare_queue(self._channel)
        logger.info("RabbitMQ | Connection established")

    async def disconnect(self) -> None:
        """
        Gracefully close channel and connection. Called during app shutdown.
        """
        try:
            if self._channel and not self._channel.is_closed:
                await self._channel.close()
                logger.info("RabbitMQ | Channel closed")

            if self._connection and not self._connection.is_closed:
                await self._connection.close()
                logger.info("RabbitMQ | Connection closed")

        except Exception as exc:
            logger.warning(f"RabbitMQ | Error during disconnect | error={exc}")

    @property
    def channel(self) -> Channel:
        """Return the shared channel. Raises if connect() was never called."""
        if self._channel is None or self._channel.is_closed:
            raise RuntimeError(
                "RabbitMQ channel is not available. "
                "Ensure RabbitMQManager.connect() completed successfully."
            )
        return self._channel

    @property
    def is_connected(self) -> bool:
        return (
            self._connection is not None
            and not self._connection.is_closed
            and self._channel is not None
            and not self._channel.is_closed
        )


# ---------------------------------------------------------------------------
# Module-level singleton used by the FastAPI app
# ---------------------------------------------------------------------------

_manager: Optional[RabbitMQManager] = None


def get_rabbitmq_manager() -> RabbitMQManager:
    """Return the module-level manager instance, creating it if necessary."""
    global _manager
    if _manager is None:
        _manager = RabbitMQManager()
    return _manager


async def connect_rabbitmq() -> None:
    """Convenience wrapper called from main.py lifespan startup."""
    await get_rabbitmq_manager().connect()


async def disconnect_rabbitmq() -> None:
    """Convenience wrapper called from main.py lifespan shutdown."""
    await get_rabbitmq_manager().disconnect()