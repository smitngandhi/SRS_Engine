from __future__ import annotations

"""
core/db/job_model.py

Defines the Job document structure stored in MongoDB.

Collection: srs_jobs

A job document tracks the full lifecycle of a single SRS generation request
from the moment the API accepts it until the worker finishes (or fails).

Document shape:
{
    "_id":          ObjectId,           # MongoDB auto-generated
    "job_id":       str,                # UUID string — exposed to the client
    "user_id":      str,                # ObjectId string of the requesting user
    "status":       str,                # See JobStatus enum below
    "progress":     int,                # 0–100
    "current_step": str,                # Human-readable current phase label
    "project_name": str,                # Pulled from SRSRequest for quick display
    "payload":      dict,               # Full SRSRequest.dict() — worker reads this
    "result_path":  str | None,         # Absolute path to generated .docx once done
    "error":        str | None,         # Error message if status == "failed"
    "created_at":   datetime (UTC),
    "updated_at":   datetime (UTC),
    "completed_at": datetime | None,    # Set when status reaches "completed"/"failed"
}
"""

from enum import Enum


class JobStatus(str, Enum):
    """
    All valid values for the `status` field.

    Using (str, Enum) means the values serialise to plain strings in JSON
    and can be compared directly with string literals.
    """
    PENDING    = "pending"      # Created, waiting in the queue
    PROCESSING = "processing"   # Worker has picked it up
    COMPLETED  = "completed"    # Document generated successfully
    FAILED     = "failed"       # Worker encountered an unrecoverable error


class JobStep(str, Enum):
    """
    Human-readable labels for each phase the worker reports.
    These are written to `current_step` as progress is updated.
    """
    QUEUED              = "Queued — waiting for a worker"
    LOADING_AGENTS      = "Loading AI agents"
    PHASE_1             = "Generating core sections (Introduction, Features, NFR …)"
    PHASE_2             = "Generating Glossary and Assumptions"
    RENDERING_DIAGRAMS  = "Rendering architecture diagrams"
    BUILDING_DOCUMENT   = "Building Word document"
    SENDING_EMAIL       = "Sending completion email"
    DONE                = "Completed"
    FAILED              = "Failed"