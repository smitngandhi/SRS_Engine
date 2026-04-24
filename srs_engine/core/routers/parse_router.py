from __future__ import annotations

"""
parse_router.py
───────────────
API routes for the Parser Agent step.

POST   /parse/srs/{file_id}          → trigger parse of an uploaded file
GET    /parse/srs/{file_id}          → fetch the UnifiedDocumentJSON
GET    /parse/srs/{file_id}/preview  → lightweight section-titles-only preview
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from srs_engine.core.auth.deps import require_user
from srs_engine.core.db.mongo import get_db
from srs_engine.core.services.parse_service import (
    get_parsed_document,
    parse_uploaded_file,
)
from srs_engine.core.services.upload_service import list_uploads
from srs_engine.schemas.upload_schemas.parse_schema import ParseStatusResponse

router = APIRouter(prefix="/parse", tags=["parse"])


def _get_upload_record(uploads: list[dict], file_id: str) -> dict:
    """Find the upload registry record for a given file_id."""
    record = next((u for u in uploads if u["file_id"] == file_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="Upload record not found. Upload the file first.")
    return record


@router.post("/srs/{file_id}")
async def trigger_parse(
    file_id: str,
    request: Request,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Trigger parsing of an already-uploaded SRS file.
    Reads from GridFS (user_uploads), writes to GridFS (parsed_docs).
    """
    user_id = str(user.get("_id"))

    # 1. Look up the file in GridFS via upload service
    uploads_data = await list_uploads(db, user_id)
    record = _get_upload_record(uploads_data, file_id)

    # 2. Trigger parse chain
    response = await parse_uploaded_file(
        db=db,
        user_id=user_id,
        file_id=file_id,
        original_filename=record["original_filename"],
        file_type=record["file_type"],
    )
    return response


@router.get("/srs/{file_id}")
async def get_parsed(
    file_id: str,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the full UnifiedDocumentJSON for a parsed file from GridFS."""
    user_id = str(user.get("_id"))
    doc = await get_parsed_document(db, user_id, file_id)
    return doc


@router.get("/srs/{file_id}/preview", response_model=ParseStatusResponse)
async def get_parse_preview(
    file_id: str,
    user=Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Lightweight preview — returns metadata + top-level section titles only.
    """
    user_id = str(user.get("_id"))
    doc = await get_parsed_document(db, user_id, file_id)

    top_level = [s.heading for s in doc.sections if s.level == 1]

    return ParseStatusResponse(
        file_id=file_id,
        parsed_doc_path=f"gridfs://{file_id}_parsed.json",
        metadata=doc.metadata,
        section_count=len(doc.sections),
        top_level_sections=top_level,
    )