from __future__ import annotations

"""
srs_engine/worker.py

Standalone SRS generation worker process.

Run with:
    python -m srs_engine.worker

The worker:
  1. Connects to MongoDB directly (no FastAPI app.state).
  2. Connects to Redis via consumer.run_consumer().
  3. On startup, recovers any jobs stuck in PROCESSING > 10 min and requeues them.
  4. For each job message received:
       a. Fetches the full job payload from MongoDB.
       b. Runs the complete SRS generation pipeline (generate_srs()).
       c. Writes progress to MongoDB at each phase checkpoint via JobRepo.
       d. Calls mark_completed() or mark_failed() when done.
       e. Sends a completion email to the user.

Scaling: MAX_WORKERS=1 enforced at worker_manager level (Groq 30k TPM limit).

Rate-limit policy
-----------------
* On a RateLimitError the worker parses the "try again in Xs" hint from
  Groq's error body and sleeps exactly that long (+ a 2 s safety buffer).
* If no hint is found it falls back to exponential backoff:
    attempt 1 → 15 s,  attempt 2 → 30 s,  attempt 3 → 60 s
* MAX_RETRIES = 3.  After exhausting retries the job is marked FAILED and
  the pipeline result is discarded — quota is NEVER touched.

Quota safety guarantee
----------------------
quota.increment_quota() is called ONLY inside _safe_increment_quota(), which
swallows its own exceptions so a quota-write failure never poisons an
already-completed job.  The quota is NEVER incremented on any failure path.
"""

import asyncio
import json
import re
import types
import logging
import certifi
from datetime import datetime, timedelta, timezone
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
from srs_engine.core.queue.redis_queue import get_redis_manager, connect_redis
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

client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
db = client[settings.mongodb_db]
logger.info(f"Worker | Connected to MongoDB | database={settings.mongodb_db}")
job_repo = JobRepo(db)
user_repo = UserRepo(db)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
# Fallback backoff schedule (seconds) indexed by attempt number (0-based).
# Only used when Groq's error body doesn't contain a retry-after hint.
_FALLBACK_BACKOFF = [15, 30, 60]
# Extra buffer added on top of Groq's own retry hint (seconds).
_RETRY_AFTER_BUFFER = 2.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_retry_after(exc: Exception) -> float | None:
    """
    Extract the "Please try again in Xs" wait time from a Groq RateLimitError.

    Groq error bodies look like:
      "...Please try again in 5.21s. Need more tokens?..."
      "...Please try again in 2m15.5s..."

    Returns the number of seconds to wait, or None if not parseable.
    """
    raw = str(exc)

    # Pattern: "try again in 5.21s"
    m = re.search(r"try again in (\d+(?:\.\d+)?)s", raw, re.IGNORECASE)
    if m:
        return float(m.group(1))

    # Pattern: "try again in 1m30s" or "try again in 1m30.5s"
    m = re.search(r"try again in (\d+)m(\d+(?:\.\d+)?)s", raw, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 60 + float(m.group(2))

    # Pattern: "try again in 2m" (no seconds component)
    m = re.search(r"try again in (\d+)m\b", raw, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 60

    return None


# ---------------------------------------------------------------------------
# Fake "app" object the service layer expects
# ---------------------------------------------------------------------------

def _make_app(session_service: InMemorySessionService) -> types.SimpleNamespace:
    """
    generate_srs() calls get_session_service(app) which accesses
    app.state.session_service_stateful. We mimic that shape here using
    a SimpleNamespace so we don't need a real FastAPI instance.

    A fresh InMemorySessionService is created per *attempt* so sessions from
    previous (failed) attempts never bleed into the retry.
    """
    state = types.SimpleNamespace(session_service_stateful=session_service)
    return types.SimpleNamespace(state=state)


# ---------------------------------------------------------------------------
# Startup recovery
# ---------------------------------------------------------------------------

async def _recover_stuck_jobs() -> None:
    """
    On startup, find jobs stuck in PROCESSING for > 10 minutes and requeue
    them. This handles the case where the worker crashed mid-job.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    stuck = await db.srs_jobs.find({
        "status": JobStatus.PROCESSING,
        "updated_at": {"$lt": cutoff}
    }).to_list(length=100)

    if not stuck:
        logger.info("Recovery | No stuck jobs found")
        return

    redis = get_redis_manager()
    for job in stuck:
        jid = job["job_id"]
        await job_repo.update_progress(jid, 0, JobStep.QUEUED, JobStatus.PENDING)
        await redis.client.rpush(settings.redis_queue_name, jid)
        logger.info(f"Recovery | Requeued stuck job | job_id={jid}")


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
# Quota helper — intentionally fire-and-forget safe
# ---------------------------------------------------------------------------

async def _safe_increment_quota(user_id: str) -> None:
    """
    Increment the docx_count quota for the user.

    This is called ONLY after a job has been successfully completed AND
    marked in MongoDB.  Any exception here is logged but does NOT alter the
    job status — the document is already delivered.

    GUARANTEE: this function is never called on any failure path.
    """
    try:
        from srs_engine.core.db.quota_repo import QuotaRepo
        quota_repo = QuotaRepo(db)
        await quota_repo.increment_quota(user_id, "docx_count")
        logger.info(f"Quota | Incremented | user_id={user_id} | type=docx_count")
    except Exception as exc:
        # Quota failure must NEVER bubble up — the job is already complete.
        logger.error(
            f"Quota | Increment failed (job already marked completed) | "
            f"user_id={user_id} | error={exc}",
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Core job handler
# ---------------------------------------------------------------------------

async def handle_job(job_id: str) -> None:
    """
    Process a single SRS generation job.

    Called by consumer.run_consumer() for every message received from Redis.
    Exceptions here cause the consumer to requeue the job.
    """
    logger.info(f"Worker | Job received | job_id={job_id}")

    # ── 1. Fetch job from MongoDB (with retry for race conditions) ─────────
    job = None
    for attempt in range(3):
        job = await job_repo.get_by_job_id(job_id)
        if job:
            break
        logger.warning(
            f"Worker | Job not found yet, retrying... (Attempt {attempt+1}/3) | job_id={job_id}"
        )
        await asyncio.sleep(2)

    if not job:
        logger.error(
            f"Worker | Job not found in DB [{settings.mongodb_db}] after retries — "
            f"skipping | job_id={job_id}"
        )
        return

    # Guard against re-processing a job that somehow landed twice in the queue.
    if job.get("status") not in (JobStatus.PENDING, JobStatus.PROCESSING):
        logger.warning(
            f"Worker | Job already in terminal state — skipping | "
            f"job_id={job_id} | status={job.get('status')}"
        )
        return

    user_id      = job["user_id"]
    payload      = job["payload"]
    project_name = job.get("project_name", "Unknown Project")

    # ── 2. Mark as processing ──────────────────────────────────────────────
    await job_repo.update_progress(
        job_id=job_id,
        progress=5,
        current_step=JobStep.LOADING_AGENTS,
        status=JobStatus.PROCESSING,
    )
    logger.info(
        f"Worker | Starting pipeline | job_id={job_id} | project={project_name}"
    )

    # ── 3. Run the generation pipeline with smart rate-limit retries ───────
    #
    #  Key invariant:  quota is only incremented in the SUCCESS branch below.
    #  On every failure path (rate limit exhausted, unexpected error) we call
    #  mark_failed() — quota is never touched.
    #
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            # Fresh session per attempt so prior state never leaks.
            session_service = InMemorySessionService()
            app = _make_app(session_service)

            result = await generate_srs(
                app=app,
                srs_data=payload,
                user_id=user_id,
                on_progress=_make_progress_callback(job_id, job_repo),
                db=db,
            )

            generated_path: str = result["srs_document_path"]
            logger.info(
                f"Worker | Pipeline complete | job_id={job_id} | path={generated_path}"
            )

            # ── SUCCESS path ───────────────────────────────────────────────
            await job_repo.mark_completed(job_id=job_id, result_path=generated_path)

            # Quota is incremented ONLY here — after confirmed completion.
            await _safe_increment_quota(user_id)

            await _notify_user(
                user_repo=user_repo,
                user_id=user_id,
                project_name=project_name,
                generated_path=generated_path,
            )

            logger.info(f"Worker | Job finished successfully | job_id={job_id}")
            return  # ← explicit return; no fall-through to failure handling

        except Exception as exc:
            import litellm

            last_exc = exc

            if isinstance(exc, litellm.exceptions.RateLimitError):
                if attempt < MAX_RETRIES - 1:
                    # Parse Groq's own hint; fall back to scheduled backoff.
                    groq_wait = _parse_retry_after(exc)
                    sleep_for = (
                        groq_wait + _RETRY_AFTER_BUFFER
                        if groq_wait is not None
                        else _FALLBACK_BACKOFF[attempt]
                    )

                    hint_str = (
                        f"{groq_wait:.1f}s (from Groq hint)"
                        if groq_wait is not None
                        else f"{sleep_for}s (fallback backoff)"
                    )
                    logger.warning(
                        f"Worker | Rate limit hit | job_id={job_id} | "
                        f"attempt={attempt+1}/{MAX_RETRIES} | sleeping {hint_str}"
                    )
                    await job_repo.update_progress(
                        job_id=job_id,
                        progress=5,
                        current_step=(
                            f"Rate limit — retrying in {sleep_for:.0f}s "
                            f"(attempt {attempt+1}/{MAX_RETRIES})"
                        ),
                        status=JobStatus.PROCESSING,
                    )
                    await asyncio.sleep(sleep_for)
                    continue  # ← go to next attempt

                # Rate limit persisted through all retries.
                logger.error(
                    f"Worker | Rate limit exhausted after {MAX_RETRIES} attempts | "
                    f"job_id={job_id} — marking FAILED, quota unchanged"
                )
            else:
                # Non-rate-limit error: fail immediately, no retries.
                logger.error(
                    f"Worker | Pipeline error | job_id={job_id} | "
                    f"attempt={attempt+1} | error={exc}",
                    exc_info=True,
                )

            # ── FAILURE path (rate limit exhausted OR unexpected error) ────
            # Quota is NOT incremented here — guaranteed by code structure.
            await job_repo.mark_failed(job_id=job_id, error=str(last_exc))
            raise last_exc  # let consumer know this job ended in failure


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
        user = await user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"_notify_user | User not found | user_id={user_id}")
            return

        notification_payload = {
            "type": "srs_complete",
            "user_id": user_id,
            "user_email": user.get("email"),
            "project_name": project_name,
            "generated_path": generated_path,
        }
        redis_mgr = get_redis_manager()
        await redis_mgr.client.rpush(
            "notification_queue", json.dumps(notification_payload)
        )
        logger.info(
            f"Worker | Notification queued for Render | project={project_name}"
        )

    except Exception as exc:
        logger.error(
            f"_notify_user | Notification push failed (job already completed) | "
            f"user_id={user_id} | error={exc}",
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--timeout", type=int, default=None,
        help="Idle timeout in seconds before exiting."
    )
    args = parser.parse_args()

    logger.info(
        "Worker | Starting up | queue=%s | timeout=%s",
        settings.redis_queue_name,
        args.timeout,
    )

    await connect_redis()
    await _recover_stuck_jobs()
    await run_consumer(handle_job, timeout=args.timeout)


if __name__ == "__main__":
    asyncio.run(main())