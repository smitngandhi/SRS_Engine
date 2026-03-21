from __future__ import annotations

"""
core/routers/srs_api.py

SRS generation API endpoints.

Changes from the original synchronous version:
  - POST /generate_srs  now returns {"job_id": "..."} immediately.
    It creates a job record in MongoDB and publishes to RabbitMQ instead of
    running the pipeline inside the request lifecycle.
  - GET  /job/{job_id}/status        one-shot status check (polling fallback).
  - GET  /job/{job_id}/status/stream SSE endpoint — streams progress updates
    until the job reaches a terminal state (completed / failed).

The enhance and auto-generate endpoints are unchanged — they are fast enough
(< 10 s) to remain synchronous.
"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from srs_engine.core.auth.deps import require_user
from srs_engine.core.db.job_model import JobStatus
from srs_engine.core.db.job_repo import JobRepo
from srs_engine.core.db.mongo import get_db
from srs_engine.core.queue.publisher import publish_srs_job
from srs_engine.core.services.srs_service import (
    auto_generate_section as auto_generate_section_service,
    enhance_problem_statement as enhance_problem_statement_service,
)
from srs_engine.schemas.home_page_schemas.auto_generate_input_schema import AutoGenerateInput
from srs_engine.schemas.home_page_schemas.problem_statement_enhance_schema import EnhanceProblemStatementInput
from srs_engine.schemas.home_page_schemas.srs_input_schema import SRSRequest

router = APIRouter()

# How often the SSE endpoint polls MongoDB for updates (seconds)
_SSE_POLL_INTERVAL = 1.0


# ---------------------------------------------------------------------------
# Unchanged endpoints
# ---------------------------------------------------------------------------

@router.post("/enhance-problem-statement")
async def enhance_problem_statement(
    request: Request,
    input_data: EnhanceProblemStatementInput,
    user=Depends(require_user),
):
    user_id = str(user.get("_id"))
    return await enhance_problem_statement_service(request.app, input_data, user_id=user_id)


@router.post("/auto-generate-section")
async def auto_generate_section(
    request: Request,
    input_data: AutoGenerateInput,
    user=Depends(require_user),
):
    user_id = str(user.get("_id"))
    return await auto_generate_section_service(request.app, input_data, user_id=user_id)


# ---------------------------------------------------------------------------
# Async job-based SRS generation
# ---------------------------------------------------------------------------

@router.post("/generate_srs")
async def generate_srs(
    request: Request,
    srs_data: SRSRequest,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Accept an SRS generation request and return a job_id immediately.

    The actual generation runs in a separate worker process.
    Use GET /job/{job_id}/status/stream to track progress.
    """
    user_id = str(user.get("_id"))
    inputs = srs_data.dict()
    project_name = inputs["project_identity"]["project_name"]

    # 1. Persist job record — worker reads the payload from here
    repo = JobRepo(db)
    job_id = await repo.create_job(
        user_id=user_id,
        project_name=project_name,
        payload=inputs,
    )

    # 2. Check RabbitMQ is available before we commit to the job
    rabbitmq = request.app.state.rabbitmq
    if rabbitmq is None or not rabbitmq.is_connected:
        await repo.mark_failed(job_id, "Message queue unavailable at request time")
        raise HTTPException(
            status_code=503,
            detail="SRS generation service is temporarily unavailable. Please try again shortly.",
        )

    # 3. Publish — worker picks this up asynchronously
    await publish_srs_job(job_id)

    return {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "message": f"SRS generation started for '{project_name}'. Use the job_id to track progress.",
    }


# ---------------------------------------------------------------------------
# Job status — one-shot polling fallback
# ---------------------------------------------------------------------------

@router.get("/job/{job_id}/status")
async def get_job_status(
    job_id: str,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Return the current state of a job as a single JSON response.
    Useful as a fallback when SSE is not supported by the client.
    """
    user_id = str(user.get("_id"))
    repo = JobRepo(db)
    job = await repo.get_by_job_id(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Prevent users from peeking at other users' jobs
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _serialize_job(job)


# ---------------------------------------------------------------------------
# SSE progress stream
# ---------------------------------------------------------------------------

@router.get("/job/{job_id}/status/stream")
async def stream_job_status(
    job_id: str,
    request: Request,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Stream real-time job progress updates via Server-Sent Events.

    The frontend should open this endpoint immediately after receiving a
    job_id from POST /generate_srs and listen until it receives a
    status of 'completed' or 'failed'.

    Event format:
        data: {"job_id": "...", "status": "...", "progress": 0-100,
               "current_step": "...", "error": null}

    The stream closes automatically once the job reaches a terminal state.

    Example (JavaScript):
        const es = new EventSource(`/job/${jobId}/status/stream`);
        es.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.status === 'completed' || data.status === 'failed') {
                es.close();
            }
        };
    """
    user_id = str(user.get("_id"))

    # Verify the job exists and belongs to this user before streaming
    repo = JobRepo(db)
    job = await repo.get_by_job_id(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return StreamingResponse(
        _sse_generator(job_id, repo, request),
        media_type="text/event-stream",
        headers={
            # Prevent proxies / nginx from buffering the stream
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


async def _sse_generator(
    job_id: str,
    repo: JobRepo,
    request: Request,
) -> AsyncGenerator[str, None]:
    """
    Async generator that polls MongoDB every second and yields SSE events.
    Terminates when:
      - job reaches a terminal status (completed / failed), or
      - the client disconnects.
    """
    terminal_states = {JobStatus.COMPLETED, JobStatus.FAILED}

    while True:
        # Stop streaming if the client has disconnected
        if await request.is_disconnected():
            break

        job = await repo.get_by_job_id(job_id)

        if job:
            payload = _serialize_job(job)
            yield f"data: {json.dumps(payload)}\n\n"

            if payload.get("status") in terminal_states:
                break

        await asyncio.sleep(_SSE_POLL_INTERVAL)


def _serialize_job(job: dict) -> dict:
    """
    Return a clean dict safe to send to the client.
    Strips internal MongoDB fields (_id, payload) and
    converts datetime objects to ISO strings.
    """
    return {
        "job_id":       job.get("job_id"),
        "status":       job.get("status"),
        "progress":     job.get("progress", 0),
        "current_step": job.get("current_step"),
        "project_name": job.get("project_name"),
        "result_path":  job.get("result_path"),
        "error":        job.get("error"),
        "created_at":   _iso(job.get("created_at")),
        "updated_at":   _iso(job.get("updated_at")),
        "completed_at": _iso(job.get("completed_at")),
    }


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


@router.get("/my-jobs")
async def list_jobs(
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Return up to 50 most recent jobs for the authenticated user.
    Called by job_tracker.js on page load.
    Route is /my-jobs (not /jobs) to avoid conflicting with the
    GET /jobs HTML page route registered in pages_router.
    """
    user_id = str(user.get("_id"))
    repo = JobRepo(db)
    jobs = await repo.get_jobs_by_user(user_id, limit=50)
    return [_serialize_job(job) for job in jobs]