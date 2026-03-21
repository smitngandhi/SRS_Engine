from __future__ import annotations

"""
core/db/job_repo.py

All MongoDB read/write operations for the `srs_jobs` collection.

Follows the exact same pattern as UserRepo:
  - Plain class, takes AsyncIOMotorDatabase in __init__
  - Every method is async
  - Callers always receive plain dicts

Field names used in the document (must stay consistent across
job_repo.py, srs_api.py, worker.py, and job_tracker.js):

  job_id        str        UUID — exposed to the client
  user_id       str        ObjectId string of the requesting user
  status        str        See JobStatus enum in job_model.py
  progress      int        0–100
  current_step  str        Human-readable phase label (JobStep values)
  project_name  str        Quick display name pulled from SRSRequest
  payload       dict       Full SRSRequest.dict() — worker reads this
  result_path   str|None   Absolute path to generated .docx once done
  error         str|None   Error message if status == "failed"
  created_at    datetime
  updated_at    datetime
  completed_at  datetime|None
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from srs_engine.core.db.job_model import JobStatus, JobStep
from srs_engine.core.logging import get_logger

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobRepo:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_job(
        self,
        user_id: str,
        project_name: str,
        payload: dict[str, Any],
    ) -> str:
        """
        Insert a new job document and return its job_id (UUID string).

        Args:
            user_id:      String representation of the user's ObjectId.
            project_name: Pulled from SRSRequest for quick display in the UI.
            payload:      The full SRSRequest.dict() so the worker has
                          everything it needs without hitting another collection.

        Returns:
            job_id — the UUID string the API returns to the client.
        """
        job_id = str(uuid.uuid4())
        now = _now()

        doc = {
            "job_id":       job_id,
            "user_id":      user_id,
            "status":       JobStatus.PENDING,
            "progress":     0,
            "current_step": JobStep.QUEUED,
            "project_name": project_name,
            "payload":      payload,
            "result_path":  None,
            "error":        None,
            "created_at":   now,
            "updated_at":   now,
            "completed_at": None,
        }

        await self.db.srs_jobs.insert_one(doc)
        logger.info(
            f"JobRepo | Job created | job_id={job_id} | "
            f"user_id={user_id} | project={project_name}"
        )
        return job_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_job_id(self, job_id: str) -> dict[str, Any] | None:
        """Fetch a job by its UUID string (the client-facing key)."""
        return await self.db.srs_jobs.find_one({"job_id": job_id})

    async def get_jobs_by_user(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Return up to `limit` jobs for a user, newest first.
        Used by GET /api/srs/jobs (job tracker page).
        """
        cursor = (
            self.db.srs_jobs
            .find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    # ------------------------------------------------------------------
    # Update — called by the worker at each pipeline checkpoint
    # ------------------------------------------------------------------

    async def update_progress(
        self,
        job_id: str,
        progress: int,
        current_step: str,
        status: str = JobStatus.PROCESSING,
    ) -> None:
        """
        Called by the worker as each phase completes.

        Args:
            job_id:       UUID string.
            progress:     Integer 0–100.
            current_step: A JobStep value or any plain string label.
            status:       Defaults to PROCESSING; pass COMPLETED/FAILED at end.
        """
        await self.db.srs_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status":       status,
                "progress":     progress,
                "current_step": current_step,
                "updated_at":   _now(),
            }},
        )
        logger.debug(
            f"JobRepo | Progress | job_id={job_id} | "
            f"{progress}% | {current_step} | status={status}"
        )

    async def mark_completed(
        self,
        job_id: str,
        result_path: str,
    ) -> None:
        """
        Mark a job as successfully completed and store the output file path.
        Sets progress to 100.
        """
        now = _now()
        await self.db.srs_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status":       JobStatus.COMPLETED,
                "progress":     100,
                "current_step": JobStep.DONE,
                "result_path":  result_path,
                "updated_at":   now,
                "completed_at": now,
            }},
        )
        logger.info(
            f"JobRepo | Completed | job_id={job_id} | path={result_path}"
        )

    async def mark_failed(
        self,
        job_id: str,
        error: str,
    ) -> None:
        """
        Mark a job as failed and store the error message.
        Called by the worker inside its except block.
        """
        now = _now()
        await self.db.srs_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status":       JobStatus.FAILED,
                "current_step": JobStep.FAILED,
                "error":        error,
                "updated_at":   now,
                "completed_at": now,
            }},
        )
        logger.error(
            f"JobRepo | Failed | job_id={job_id} | error={error}"
        )