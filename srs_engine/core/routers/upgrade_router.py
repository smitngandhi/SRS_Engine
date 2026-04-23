from __future__ import annotations

"""
upgrade_router.py
─────────────────
API routes for the SRS Upgrader pipeline.

POST  /upgrade/srs/{file_id}/session    → create session (snapshot sections)
POST  /upgrade/srs/{file_id}/analyse    → run section analyser agent
POST  /upgrade/srs/{file_id}/questions  → generate questions for flagged sections
POST  /upgrade/srs/{file_id}/answers    → submit user answers
PATCH /upgrade/srs/{file_id}/section/{section_id} → accept / reject / edit
GET   /upgrade/srs/{file_id}/session    → get current session state
GET   /upgrade/srs/{file_id}/export     → get assembled final document
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
import asyncio
import json as _json
from pydantic import BaseModel, ConfigDict


from srs_engine.core.db.mongo import get_db
from srs_engine.core.db.quota_repo import QuotaRepo

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

from srs_engine.core.auth.deps import require_user
from srs_engine.core.services.upgrade_service import (
    assemble_final_document,
    create_upgrade_session,
    get_upgrade_session,
    run_analysis,
    run_question_generation,
    submit_answers,
    update_section_status,
)
from srs_engine.schemas.upgrader_schemas.upgrade_session_schema import AnswerSubmission

router = APIRouter(prefix="/upgrade", tags=["upgrade"])

# ── Per-job progress queues (in-memory, keyed by file_id) ────────────────────
# upgrade_service.py writes section-level events here via put_progress()
_progress_queues: dict[str, asyncio.Queue] = {}

def get_or_create_queue(file_id: str) -> asyncio.Queue:
    if file_id not in _progress_queues:
        _progress_queues[file_id] = asyncio.Queue()
    return _progress_queues[file_id]

async def put_progress(file_id: str, event: dict) -> None:
    """Called by upgrade_service to push a progress event."""
    q = _progress_queues.get(file_id)
    if q:
        await q.put(event)


# ── Request bodies ────────────────────────────────────────────────────────────

class SectionActionRequest(StrictBaseModel):
    action: str               # "accept" | "reject" | "edit"
    edited_content: str = ""  # only required when action == "edit"


class AnswerBatchRequest(StrictBaseModel):
    submissions: list[AnswerSubmission]


class AnalyseRequest(StrictBaseModel):
    score_threshold: float = 6.5  # sections below this are flagged


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/srs/{file_id}/session")
async def create_session(
    file_id: str,
    request: Request,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Create an UpgradeSession for a parsed file.
    Snapshots all sections — must be called before /analyse.
    Idempotent: calling again overwrites the previous session.
    """
    user_id = str(user.get("_id"))
    session = await create_upgrade_session(db, user_id=user_id, file_id=file_id)
    return {
        "success": True,
        "file_id": file_id,
        "sections_snapshotted": len(session.sections),
        "pipeline_status": session.pipeline_status,
    }


@router.get("/srs/{file_id}/progress")
async def progress_stream(
    file_id: str,
    request: Request,
    user=Depends(require_user),
):
    """
    SSE stream — yields progress events while /analyse and /questions are running.
    Frontend subscribes with EventSource before calling /analyse.
    """
    q = get_or_create_queue(file_id)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"data: {_json.dumps(event)}\n\n"
                    if event.get("type") == "done":
                        break
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield "data: {\"type\": \"heartbeat\"}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/srs/{file_id}/analyse")
async def analyse_sections(
    file_id: str,
    body: AnalyseRequest,
    request: Request,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Run the section analyser agent on all sections concurrently.
    Auto-creates session if not yet created.
    """
    user_id = str(user.get("_id"))

    # Auto-create session if missing (handled inside run_analysis now)
    session = await run_analysis(
        db=db,
        user_id=user_id,
        file_id=file_id,
        score_threshold=body.score_threshold,
    )

    return {
        "success": True,
        "file_id": file_id,
        "sections_analysed": len(session.sections),
        "sections_needing_upgrade": len(session.sections_needing_upgrade),
        "pipeline_status": session.pipeline_status,
        "upgrade_summary": session.upgrade_summary,
        "sections": session.sections,
    }


@router.post("/srs/{file_id}/questions")
async def generate_questions(
    file_id: str,
    request: Request,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Generate clarifying questions for all flagged sections.
    Must be called after /analyse.
    """
    user_id = str(user.get("_id"))
    session = await run_question_generation(db=db, user_id=user_id, file_id=file_id)

    sections_with_questions = [
        s for s in session.sections if s.questions
    ]

    return {
        "success": True,
        "file_id": file_id,
        "sections_with_questions": len(sections_with_questions),
        "pipeline_status": session.pipeline_status,
        "sections": session.sections,
    }


@router.post("/srs/{file_id}/answers")
async def submit_section_answers(
    file_id: str,
    body: AnswerBatchRequest,
    request: Request,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Submit user answers for one or more flagged sections.
    Sections with all questions answered are marked 'answered'.
    Pipeline advances to 'ready' when all flagged sections are answered.
    """
    user_id = str(user.get("_id"))
    session = await submit_answers(
        db=db,
        user_id=user_id,
        file_id=file_id,
        submissions=body.submissions,
    )

    return {
        "success": True,
        "file_id": file_id,
        "pipeline_status": session.pipeline_status,
        "upgrade_summary": session.upgrade_summary,
        "pending_questions": len(session.sections_pending_questions),
    }


@router.patch("/srs/{file_id}/section/{section_id}")
async def act_on_section(
    file_id: str,
    section_id: str,
    body: SectionActionRequest,
    request: Request,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Accept, reject, or edit the upgraded content for a section.
    action: "accept" | "reject" | "edit"
    edited_content: required when action == "edit"
    """
    user_id = str(user.get("_id"))
    session = await update_section_status(
        db=db,
        user_id=user_id,
        file_id=file_id,
        section_id=section_id,
        action=body.action,
        edited_content=body.edited_content,
    )

    return {
        "success": True,
        "section_id": section_id,
        "new_status": next(
            (s.status for s in session.sections if s.section_id == section_id), None
        ),
        "pipeline_status": session.pipeline_status,
        "upgrade_summary": session.upgrade_summary,
    }


@router.get("/srs/{file_id}/session")
async def get_session(
    file_id: str,
    request: Request,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the full current session state."""
    user_id = str(user.get("_id"))
    session = await get_upgrade_session(db, user_id, file_id)
    return session


@router.get("/srs/{file_id}/export")
async def export_final_document(
    file_id: str,
    request: Request,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Assemble and return the final upgraded document.
    Headings and structure always come from the original parsed tree.
    Only content fields are selectively replaced from accepted/edited sections.
    """
    user_id = str(user.get("_id"))
    doc = await assemble_final_document(db=db, user_id=user_id, file_id=file_id)
    return doc