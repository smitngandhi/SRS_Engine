from __future__ import annotations

"""
srs_engine/worker.py

Standalone SRS generation worker process.

Run with:
    python -m srs_engine.worker

The worker:
  1. Connects to MongoDB directly (no FastAPI app.state).
  2. Connects to RabbitMQ via consumer.run_consumer().
  3. For each job message received:
       a. Fetches the full job payload from MongoDB.
       b. Runs the complete SRS generation pipeline (generate_srs()).
       c. Writes progress to MongoDB at each phase checkpoint via JobRepo.
       d. Calls mark_completed() or mark_failed() when done.
       e. Sends a completion email to the user.

Scaling: start multiple workers with the same command in separate terminals
(or Docker containers). RabbitMQ distributes jobs across all running workers
with prefetch_count=1 so no worker hogs multiple jobs.
"""

import asyncio
import types
import logging
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from motor.motor_asyncio import AsyncIOMotorClient
from google.adk.sessions import InMemorySessionService

from srs_engine.core.config import get_settings
from srs_engine.core.db.job_model import JobStatus, JobStep
from srs_engine.core.db.job_repo import JobRepo
from srs_engine.core.db.user_repo import UserRepo
from srs_engine.core.logging.config import setup_logging
from srs_engine.core.logging import get_logger
from srs_engine.core.queue.consumer import run_consumer
from srs_engine.core.services.email_service import send_srs_complete_email
from srs_engine.core.services.srs_service import generate_srs


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

settings = get_settings()
setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)
logger = get_logger("srs_engine.worker")


# ---------------------------------------------------------------------------
# MongoDB bootstrap (global connection pool for worker)
# ---------------------------------------------------------------------------

client = AsyncIOMotorClient(settings.mongodb_uri)
db = client[settings.mongodb_db]
job_repo = JobRepo(db)
user_repo = UserRepo(db)


# ---------------------------------------------------------------------------
# Fake "app" object the service layer expects
# ---------------------------------------------------------------------------

def _make_app(session_service: InMemorySessionService) -> types.SimpleNamespace:
    """
    generate_srs() calls get_session_service(app) which accesses
    app.state.session_service_stateful. We mimic that shape here using
    a SimpleNamespace so we don't need a real FastAPI instance.

    A fresh InMemorySessionService is created per job so sessions from
    different jobs never bleed into each other.
    """
    state = types.SimpleNamespace(session_service_stateful=session_service)
    return types.SimpleNamespace(state=state)


# ---------------------------------------------------------------------------
# Progress callback factory
# ---------------------------------------------------------------------------

def _make_progress_callback(job_id: str, repo: JobRepo):
    """
    Return an async callback that writes a progress update to MongoDB.
    Passed to generate_srs() as on_progress=.
    """
    async def on_progress(progress: int, step: str) -> None:
        await repo.update_progress(
            job_id=job_id,
            progress=progress,
            current_step=step,
            status=JobStatus.PROCESSING,
        )
    return on_progress


# ---------------------------------------------------------------------------
# Core job handler
# ---------------------------------------------------------------------------

async def handle_job(job_id: str) -> None:
    """
    Process a single SRS generation job.

    Called by consumer.run_consumer() for every message received from
    RabbitMQ. Exceptions here cause the consumer to NACK the message
    (requeue=False) so it moves to the dead-letter queue.
    """
    logger.info(f"Worker | Job received | job_id={job_id}")

    # ── 1. Fetch job from MongoDB ──────────────────────────────────────
    job = await job_repo.get_by_job_id(job_id)
    if not job:
        logger.error(f"Worker | Job not found in DB — skipping | job_id={job_id}")
        return

    # Guard against re-processing a job that somehow landed twice in the queue
    if job.get("status") not in (JobStatus.PENDING, JobStatus.PROCESSING):
        logger.warning(
            f"Worker | Job already in terminal state — skipping | "
            f"job_id={job_id} | status={job.get('status')}"
        )
        return

    user_id      = job["user_id"]
    payload      = job["payload"]
    project_name = job.get("project_name", "Unknown Project")

    # ── 2. Mark as processing ──────────────────────────────────────────
    await job_repo.update_progress(
        job_id=job_id,
        progress=5,
        current_step=JobStep.LOADING_AGENTS,
        status=JobStatus.PROCESSING,
    )
    logger.info(f"Worker | Starting pipeline | job_id={job_id} | project={project_name}")

    # ── 3. Run the generation pipeline ────────────────────────────────
    try:
        session_service = InMemorySessionService()
        app = _make_app(session_service)

        result = await generate_srs(
            app=app,
            srs_data=payload,           # plain dict — generate_srs handles both
            user_id=user_id,
            on_progress=_make_progress_callback(job_id, job_repo),
        )

        generated_path: str = result["srs_document_path"]
        logger.info(
            f"Worker | Pipeline complete | job_id={job_id} | path={generated_path}"
        )

        # ── 4. Mark completed ──────────────────────────────────────────
        await job_repo.mark_completed(job_id=job_id, result_path=generated_path)

        # ── 5. Send completion email ───────────────────────────────────
        await _notify_user(
            user_repo=user_repo,
            user_id=user_id,
            project_name=project_name,
            generated_path=generated_path,
        )

    except Exception as exc:
        error_msg = str(exc)
        logger.error(
            f"Worker | Pipeline failed | job_id={job_id} | error={error_msg}",
            exc_info=True,
        )
        await job_repo.mark_failed(job_id=job_id, error=error_msg)
        # Re-raise so the consumer sends NACK to RabbitMQ
        raise


# ---------------------------------------------------------------------------
# Email notification helper
# ---------------------------------------------------------------------------

async def _notify_user(
    *,
    user_repo: UserRepo,
    user_id: str,
    project_name: str,
    generated_path: str,
) -> None:
    """
    Look up the user's email and send a completion notification.
    Failures here are logged but do NOT fail the job — the document
    is already generated and marked completed in MongoDB.
    """
    try:
        # Update progress to "Sending email" (95%) before the network call
        # NOTE: We don't have job_repo here by design — this is fire-and-forget
        # after mark_completed. The status is already COMPLETED in MongoDB.

        user = await user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"_notify_user | User not found | user_id={user_id}")
            return

        user_email        = user.get("email")
        user_display_name = user.get("display_name") or user.get("username") or "User"

        await send_srs_complete_email(
            settings=settings,
            to_email=user_email,
            user_display_name=user_display_name,
            project_name=project_name,
            document_path=generated_path,
        )

    except Exception as exc:
        # Email failure must never bubble up and mark the job as failed
        logger.error(
            f"_notify_user | Email send failed (job already completed) | "
            f"user_id={user_id} | error={exc}",
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=None, help="Idle timeout in seconds before exiting.")
    args = parser.parse_args()

    logger.info("Worker | Starting up | queue=%s | timeout=%s", settings.rabbitmq_srs_queue, args.timeout)
    await run_consumer(handle_job, timeout=args.timeout)


if __name__ == "__main__":
    asyncio.run(main())