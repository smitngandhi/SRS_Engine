from __future__ import annotations

"""
schemas/job_schema.py

Defines the job document structure and status constants used across the
API, worker, and SSE endpoint. Keeping these in schemas/ means no layer
imports from another layer just to read a status string.

Job document shape (as stored in MongoDB):
{
    "_id":              ObjectId          — internal Mongo PK
    "job_id":           str (UUID4)       — exposed to the client
    "user_id":          str               — owner's ObjectId as string
    "status":           str               — see JobStatus below
    "progress":         int  0-100        — percentage complete
    "progress_message": str               — human-readable current step
    "srs_data":         dict              — full SRSRequest payload
    "result":           dict | None       — {"srs_document_path": "..."} on success
    "error":            str | None        — error message on failure
    "created_at":       datetime (UTC)
    "updated_at":       datetime (UTC)
    "completed_at":     datetime | None   — set when status → completed/failed
}
"""


class JobStatus:
    PENDING    = "pending"      # created, message published, worker not yet picked up
    PROCESSING = "processing"   # worker has started executing the pipeline
    COMPLETED  = "completed"    # document generated successfully
    FAILED     = "failed"       # unrecoverable error during generation


# Maps each pipeline stage to the progress percentage it represents.
# The worker imports this and calls job_repo.update_progress() at each stage.
PROGRESS_STEPS: dict[str, int] = {
    "queued":                   0,
    "starting":                 5,
    "phase1_agents_running":   20,
    "phase1_complete":         45,
    "phase2_agents_running":   55,
    "phase2_complete":         70,
    "diagrams_rendering":      75,
    "diagrams_complete":       85,
    "document_generating":     90,
    "document_complete":      100,
}