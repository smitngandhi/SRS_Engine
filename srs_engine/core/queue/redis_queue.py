from __future__ import annotations

"""
core/queue/redis_queue.py

Drop-in replacement for rabbitmq.py using Redis via RPOPLPUSH reliable queue
pattern. Exposes the same connect/disconnect/get_manager interface.

Also provides Redis-based semaphore helpers for concurrency control on
diagram generation and section upgrades.
"""

import redis.asyncio as aioredis

from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger

logger = get_logger(__name__)

# Module-level singleton
_redis_manager: "RedisManager | None" = None


class RedisManager:
    def __init__(self):
        self._client: aioredis.Redis | None = None
        self._settings = get_settings()

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            self._settings.redis_url,
            decode_responses=False,  # We handle bytes manually
            ssl_cert_reqs=None,      # Required for some Upstash/Cloud Redis setups
        )
        await self._client.ping()
        logger.info("Redis | Connected | url=%s", self._settings.redis_url)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Redis | Disconnected")

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> aioredis.Redis:
        if self._client is None:
            raise RuntimeError("Redis not connected — call connect() first")
        return self._client

    # ── Semaphore helpers ────────────────────────────────────────────────

    async def acquire_semaphore(self, name: str, timeout: int = 90) -> bool:
        """
        Try to acquire a Redis-based semaphore (atomic SET NX EX).
        Returns True if acquired, False if already locked.
        """
        acquired = await self._client.set(f"sem:{name}", "1", nx=True, ex=timeout)
        return bool(acquired)

    async def release_semaphore(self, name: str) -> None:
        """Release a previously acquired semaphore."""
        await self._client.delete(f"sem:{name}")


# ── Module-level helpers (mirror rabbitmq.py pattern) ────────────────────────

def get_redis_manager() -> RedisManager:
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


async def connect_redis() -> None:
    manager = get_redis_manager()
    await manager.connect()


async def disconnect_redis() -> None:
    manager = get_redis_manager()
    await manager.disconnect()
