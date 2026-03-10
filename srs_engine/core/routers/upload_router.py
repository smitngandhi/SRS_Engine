from __future__ import annotations

"""
upload_router.py
────────────────
API routes for the SRS Upgrader upload step.

POST   /upload/srs          → upload a PDF or DOCX
GET    /upload/srs/list     → list all uploads for current user
DELETE /upload/srs/{file_id} → delete a specific upload
"""

from fastapi import APIRouter, Depends, Request, UploadFile, File

from srs_engine.core.auth.deps import require_user
from srs_engine.core.services.upload_service import (
    delete_upload,
    list_uploads,
    save_upload,
)

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/srs")
async def upload_srs(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(require_user),
):
    """Upload a PDF or DOCX SRS document. Requires authentication."""
    user_id = str(user.get("_id"))
    record = await save_upload(user_id, file)
    return {
        "success": True,
        "file": record,
    }


@router.get("/srs/list")
async def list_srs_uploads(
    request: Request,
    user=Depends(require_user),
):
    """Return all uploaded SRS files for the current user."""
    user_id = str(user.get("_id"))
    files = await list_uploads(user_id)
    return {"files": files}


@router.delete("/srs/{file_id}")
async def delete_srs_upload(
    file_id: str,
    request: Request,
    user=Depends(require_user),
):
    """Delete an uploaded file by its file_id."""
    user_id = str(user.get("_id"))
    await delete_upload(user_id, file_id)
    return {"success": True, "deleted_file_id": file_id}