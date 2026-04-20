from __future__ import annotations

"""
srs_engine/worker_manager.py

An intelligent auto-scaler for SRS workers. 
It monitors both:
  1. RabbitMQ queue depth (jobs waiting to be processed)
  2. Job progress in MongoDB (currently running jobs)

Workers are spawned based on:
  - If there are pending jobs in the queue
  - If a running job reaches 75% progress and more jobs are waiting
  
This ensures smooth scaling: when a job is mostly done, we can start
the next job on a new worker, so the first worker finishes without blocking.

Usage:
    python -m srs_engine.worker_manager
"""

import asyncio
import subprocess
import os
import signal
import sys
import aio_pika
from typing import List
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger
from srs_engine.core.db.job_repo import JobRepo
from srs_engine.core.db.job_model import JobStatus

logger = get_logger("srs_engine.worker_manager")
settings = get_settings()

MAX_WORKERS = 4  # Limit to 4 parallel workers to avoid OOM or API rate limits
POLL_INTERVAL = 5 # seconds
PROGRESS_THRESHOLD = 75  # Spawn new worker when a job reaches 75%

active_processes: List[subprocess.Popen] = []
mongodb_client = None
job_repo = None

def _build_url() -> str:
    return (
        f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}"
        f"@{settings.rabbitmq_host}:{settings.rabbitmq_port}{settings.rabbitmq_vhost}"
    )

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


async def get_running_jobs_progress() -> dict[str, int]:
    """
    Query MongoDB to get progress of all currently running jobs.
    
    Returns:
        A dict mapping job_id -> progress (0-100)
    """
    global job_repo
    if not job_repo:
        return {}
    
    try:
        cursor = job_repo.db.srs_jobs.find({"status": JobStatus.PROCESSING})
        jobs = await cursor.to_list(length=None)
        
        return {job["job_id"]: job.get("progress", 0) for job in jobs}
    except Exception as e:
        logger.warning(f"Manager | Failed to query running jobs: {e}")
        return {}


async def should_spawn_worker_for_progress(queue_depth: int) -> bool:
    """
    Check if we should spawn a new worker based on job progress.
    
    Returns True if:
      - A job is at or above the PROGRESS_THRESHOLD
      - AND there are more jobs waiting in the queue
      - AND we have room for more workers
    """
    if len(active_processes) >= MAX_WORKERS:
        return False
    
    if queue_depth == 0:
        return False
    
    running_jobs = await get_running_jobs_progress()
    
    # Check if any job has reached the threshold
    for job_id, progress in running_jobs.items():
        if progress >= PROGRESS_THRESHOLD:
            logger.info(
                f"Manager | Job {job_id[:8]}... reached {progress}% progress | "
                f"Queue depth: {queue_depth} | Spawning new worker"
            )
            return True
    
    return False


async def monitor_queue():
    """Poll RabbitMQ and MongoDB to manage workers based on load and progress."""
    url = _build_url()
    queue_name = settings.rabbitmq_srs_queue
    
    try:
        connection = await aio_pika.connect_robust(url)
    except Exception as e:
        logger.error(f"Manager | Failed to connect to RabbitMQ: {e}")
        return

    async with connection:
        channel = await connection.channel()
        
        while True:
            # Clean up dead processes
            global active_processes
            active_processes = [p for p in active_processes if p.poll() is None]

            # Declare queue passively to get stats
            try:
                queue = await channel.declare_queue(queue_name, durable=True, passive=True)
                ready_messages = queue.declaration_result.message_count
                
                # Spawn based on queue depth (if jobs are waiting)
                if ready_messages > 0 and len(active_processes) < MAX_WORKERS:
                    # First, check if we should spawn based on progress threshold
                    if await should_spawn_worker_for_progress(ready_messages):
                        spawn_worker(timeout=300)
                    # Otherwise, spawn based on basic queue depth
                    elif len(active_processes) == 0:
                        spawn_worker() # Ensure at least 1 worker is running
                
                # Minimum 1 worker always running (the Persistent one)
                if len(active_processes) == 0:
                    spawn_worker() # No timeout for the first one

                if ready_messages > 0 or len(active_processes) > 0:
                    logger.info(
                        f"Manager | Queue depth: {ready_messages} | "
                        f"Active workers: {len(active_processes)} | "
                        f"Progress threshold: {PROGRESS_THRESHOLD}%"
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
        except:
            pass
    
    # Close MongoDB connection
    if mongodb_client:
        try:
            mongodb_client.close()
        except:
            pass
    
    sys.exit(0)

if __name__ == "__main__":
    # Register termination signals
    signal.signal(signal.SIGINT, cleanup_workers)
    signal.signal(signal.SIGTERM, cleanup_workers)

    logger.info(f"Manager | Starting worker auto-scaler (Max: {MAX_WORKERS})")
    logger.info(f"Manager | Progress threshold: {PROGRESS_THRESHOLD}%")
    
    # Initialize MongoDB connection for progress monitoring
    try:
        mongodb_client = AsyncIOMotorClient(settings.mongodb_uri)
        db = mongodb_client[settings.mongodb_db]
        job_repo = JobRepo(db)
        logger.info("Manager | MongoDB connection established")
    except Exception as e:
        logger.error(f"Manager | Failed to connect to MongoDB: {e}")
        logger.warning("Manager | Will still monitor queue depth, but progress-based scaling disabled")
        job_repo = None
        mongodb_client = None
    
    # Start the first worker immediately
    spawn_worker()
    
    try:
        asyncio.run(monitor_queue())
    except KeyboardInterrupt:
        cleanup_workers(None, None)
