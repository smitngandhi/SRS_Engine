from __future__ import annotations

"""
srs_engine/worker_manager.py

A simple auto-scaler for SRS workers. 
It monitors the RabbitMQ queue depth and spawns new python worker processes 
as needed, up to a maximum limit.

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

from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger

logger = get_logger("srs_engine.worker_manager")
settings = get_settings()

MAX_WORKERS = 4  # Limit to 4 parallel workers to avoid OOM or API rate limits
POLL_INTERVAL = 5 # seconds

active_processes: List[subprocess.Popen] = []

def _build_url() -> str:
    return (
        f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}"
        f"@{settings.rabbitmq_host}:{settings.rabbitmq_port}{settings.rabbitmq_vhost}"
    )

def spawn_worker(timeout: int | None = None):
    """Spawn a new worker process."""
    if len(active_processes) >= MAX_WORKERS:
        return

    msg = f"Manager | Spawning new worker (Current total: {len(active_processes) + 1})"
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
    """Poll RabbitMQ and manage workers based on load."""
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
                
                # If there are jobs waiting and we have room, scale up
                # Extra workers get a 5-minute (300s) idle timeout
                if ready_messages > 0 and len(active_processes) < MAX_WORKERS:
                    spawn_worker(timeout=300)
                
                # Minimum 1 worker always running (the Persistent one)
                if len(active_processes) == 0:
                    spawn_worker() # No timeout for the first one

                if ready_messages > 0:
                    logger.info(f"Manager | Queue depth: {ready_messages} | Active workers: {len(active_processes)}")

            except Exception as e:
                logger.warning(f"Manager | Warning polling queue: {e}")

            await asyncio.sleep(POLL_INTERVAL)

def cleanup_workers(sig, frame):
    """Kill all child processes on exit."""
    logger.info("Manager | Shutting down. Cleaning up workers...")
    for p in active_processes:
        p.terminate()
    sys.exit(0)

if __name__ == "__main__":
    # Register termination signals
    signal.signal(signal.SIGINT, cleanup_workers)
    signal.signal(signal.SIGTERM, cleanup_workers)

    logger.info(f"Manager | Starting worker auto-scaler (Max: {MAX_WORKERS})")
    
    # Start the first worker immediately
    spawn_worker()
    
    try:
        asyncio.run(monitor_queue())
    except KeyboardInterrupt:
        cleanup_workers(None, None)
