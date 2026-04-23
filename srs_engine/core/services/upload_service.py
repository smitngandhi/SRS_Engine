from __future__ import annotations

"""
upload_service.py
─────────────────
Handles all business logic for the SRS Upgrader upload step:
  - MIME / extension validation
  - Saving to  user_uploads/{user_id}/{pdf|docx}/
  - Writing / reading a per-user  file_registry.json
  - Listing and deleting uploaded files
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile

# ── Constants ────────────────────────────────────────────────────────────────

UPLOAD_ROOT = Path("./user_uploads")

ALLOWED_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    # browsers sometimes send this for .docx
    "application/msword": "docx",
    # fallback when browser sends octet-stream but extension is right
    "application/octet-stream": None,   # resolved via extension below
}

ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
}

MAX_FILE_SIZE_MB = 20


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _registry_path(user_id: str) -> Path:
    return UPLOAD_ROOT / user_id / "file_registry.json"


def _load_registry(user_id: str) -> list[dict]:
    path = _registry_path(user_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_registry(user_id: str, records: list[dict]) -> None:
    path = _registry_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, default=str, indent=2), encoding="utf-8")


def _resolve_file_type(content_type: str, filename: str) -> str:
    """Return 'pdf' or 'docx', or raise 422 if unsupported."""
    # Try MIME first
    file_type = ALLOWED_MIME_TYPES.get(content_type)
    if file_type:
        return file_type

    # octet-stream → fall through to extension check
    suffix = Path(filename).suffix.lower()
    file_type = ALLOWED_EXTENSIONS.get(suffix)
    if file_type:
        return file_type

    raise HTTPException(
        status_code=422,
        detail=(
            f"Unsupported file type '{content_type}' / extension '{suffix}'. "
            "Only PDF and DOCX files are accepted."
        ),
    )


from srs_engine.core.db.file_storage import FileStorage
from motor.motor_asyncio import AsyncIOMotorDatabase

# ── Public service functions ──────────────────────────────────────────────────

async def save_upload(db: AsyncIOMotorDatabase, user_id: str, file: UploadFile) -> dict:
    """
    Validate, store in GridFS, and return the record.
    Limit: max 10 files per user.
    """
    storage = FileStorage(db)
    
    # 1. Quota Check (Hard Limit: 10)
    existing = await storage.list_files({"type": "upload", "user_id": user_id})
    if len(existing) >= 10:
        raise HTTPException(
            status_code=429,
            detail="You've reached the upload limit (10 files). Please delete old uploads to continue.",
        )

    content_type = file.content_type or ""
    filename = file.filename or "upload"

    # Resolve type
    file_type = _resolve_file_type(content_type, filename)

    # Read content
    content = await file.read()
    size_bytes = len(content)

    if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB.")
    if size_bytes == 0:
        raise HTTPException(status_code=422, detail="File is empty.")

    # 2. Save to GridFS
    metadata = {
        "type": "upload",
        "user_id": user_id,
        "file_type": file_type,
        "original_filename": filename,
        "uploaded_at": _now().isoformat(),
        "size_kb": round(size_bytes / 1024, 1),
    }
    
    grid_file_id = await storage.save_file(content, filename, metadata)

    return {
        "file_id": grid_file_id,
        "original_filename": filename,
        "file_type": file_type,
        "size_kb": round(size_bytes / 1024, 1),
        "uploaded_at": metadata["uploaded_at"],
        "user_id": user_id,
    }


async def list_uploads(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    """Return all uploaded files for a user from GridFS."""
    storage = FileStorage(db)
    files = await storage.list_files({"type": "upload", "user_id": user_id})
    
    records = []
    for f in files:
        records.append({
            "file_id": f["file_id"],
            "original_filename": f["metadata"].get("original_filename", f["filename"]),
            "file_type": f["metadata"].get("file_type"),
            "size_kb": f["metadata"].get("size_kb"),
            "uploaded_at": f["metadata"].get("uploaded_at"),
            "user_id": user_id,
        })
    
    return list(reversed(records))


async def delete_upload(db: AsyncIOMotorDatabase, user_id: str, file_id: str) -> None:
    """Delete a file from GridFS."""
    storage = FileStorage(db)
    # Verify ownership
    files = await storage.list_files({"type": "upload", "user_id": user_id})
    target = next((f for f in files if f["file_id"] == file_id), None)

    if not target:
        raise HTTPException(status_code=404, detail="File not found or access denied.")

    await storage.delete_file_by_id(file_id)


async def get_upload_content(db: AsyncIOMotorDatabase, file_id: str) -> bytes:
    """Retrieve raw file bytes from GridFS."""
    storage = FileStorage(db)
    content = await storage.get_file_by_id(file_id)
    if not content:
        raise HTTPException(status_code=404, detail="File content not found.")
    return content