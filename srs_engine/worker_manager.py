from __future__ import annotations

"""
srs_engine/worker_manager.py

Simplified worker manager for the Redis-based queue.
Monitors MongoDB job status and ensures the single persistent worker
(MAX_WORKERS=1) is always running.

MAX_WORKERS=1 is enforced because Groq free tier has a 30k TPM rate limit —
running multiple workers causes rate-limit errors that fail jobs silently.

Usage:
    python -m srs_engine.worker_manager
"""

import asyncio
import subprocess
import sys
import signal
import os
from typing import List

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger
from srs_engine.core.db.job_repo import JobRepo
from srs_engine.core.db.job_model import JobStatus

logger = get_logger("srs_engine.worker_manager")
settings = get_settings()

MAX_WORKERS = 1   # Groq 30k TPM rate limit — only 1 concurrent worker
POLL_INTERVAL = 5  # seconds

active_processes: List[subprocess.Popen] = []
mongodb_client = None
job_repo = None


def spawn_worker(timeout: int | None = None):
    """Spawn a new worker process."""
    if len(active_processes) >= MAX_WORKERS:
        return

    msg = f"Manager | Spawning new worker (Current total: {len(active_processes) + 1}/{MAX_WORKERS})"
    if timeout:
        msg += f" with idle timeout of {timeout}s"
    else:
        msg += " (Persistent)"

    logger.info(msg)

    cmd = [sys.executable, "-m", "srs_engine.worker"]
    if timeout:
        cmd.extend(["--timeout", str(timeout)])

    proc = subprocess.Popen(cmd)
    active_processes.append(proc)


async def monitor_queue():
    """Poll Redis LLEN and MongoDB to ensure the persistent worker is alive."""
    client = aioredis.from_url(settings.redis_url, decode_responses=False)
    queue_name = settings.redis_queue_name

    logger.info(f"Manager | Monitoring Redis queue | queue={queue_name}")

    while True:
        # Clean up dead processes
        global active_processes
        active_processes = [p for p in active_processes if p.poll() is None]

        try:
            queue_depth = await client.llen(queue_name)

            # Always keep the persistent worker running
            if len(active_processes) == 0:
                logger.info("Manager | No active workers — spawning persistent worker")
                spawn_worker()

            if queue_depth > 0 or len(active_processes) > 0:
                logger.info(
                    f"Manager | Queue depth: {queue_depth} | "
                    f"Active workers: {len(active_processes)}/{MAX_WORKERS}"
                )

        except Exception as e:
            logger.warning(f"Manager | Warning polling queue: {e}")

        await asyncio.sleep(POLL_INTERVAL)


def cleanup_workers(sig, frame):
    """Kill all child processes on exit."""
    global mongodb_client
    logger.info("Manager | Shutting down. Cleaning up workers...")
    for p in active_processes:
        try:
            p.terminate()
        except Exception:
            pass

    if mongodb_client:
        try:
            mongodb_client.close()
        except Exception:
            pass

    sys.exit(0)


if __name__ == "__main__":
    # Register termination signals
    signal.signal(signal.SIGINT, cleanup_workers)
    signal.signal(signal.SIGTERM, cleanup_workers)

    logger.info(f"Manager | Starting worker auto-scaler (Max: {MAX_WORKERS})")

    # Initialize MongoDB connection for progress monitoring
    try:
        mongodb_client = AsyncIOMotorClient(settings.mongodb_uri)
        db = mongodb_client[settings.mongodb_db]
        job_repo = JobRepo(db)
        logger.info("Manager | MongoDB connection established")
    except Exception as e:
        logger.error(f"Manager | Failed to connect to MongoDB: {e}")
        job_repo = None
        mongodb_client = None

    # Start the persistent worker immediately
    spawn_worker()

    try:
        asyncio.run(monitor_queue())
    except KeyboardInterrupt:
        cleanup_workers(None, None)
