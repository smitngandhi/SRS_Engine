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


# ── Public service functions ──────────────────────────────────────────────────

async def save_upload(user_id: str, file: UploadFile) -> dict:
    """
    Validate, store, and register an uploaded file.
    Returns the registry record dict.
    """
    content_type = file.content_type or ""
    filename = file.filename or "upload"

    # Resolve type (raises 422 on invalid)
    file_type = _resolve_file_type(content_type, filename)

    # Read content
    content = await file.read()

    # Size check
    size_bytes = len(content)
    if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_FILE_SIZE_MB} MB limit.",
        )
    if size_bytes == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    # Build storage path:  user_uploads/{user_id}/{pdf|docx}/{uuid}_{original_name}
    file_id = str(uuid.uuid4())
    safe_name = Path(filename).name  # strip any path components
    dest_dir = UPLOAD_ROOT / user_id / file_type
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{file_id}_{safe_name}"

    # Write to disk
    dest_path.write_bytes(content)

    # Build registry record
    record = {
        "file_id": file_id,
        "original_filename": safe_name,
        "file_type": file_type,
        "size_kb": round(size_bytes / 1024, 1),
        "uploaded_at": _now().isoformat(),
        "storage_path": str(dest_path),
        "user_id": user_id,
    }

    # Append to registry
    records = _load_registry(user_id)
    records.append(record)
    _save_registry(user_id, records)

    return record


async def list_uploads(user_id: str) -> list[dict]:
    """Return all uploaded files for a user (most recent first)."""
    records = _load_registry(user_id)
    # Verify files still exist on disk (clean up stale entries)
    valid = [r for r in records if Path(r["storage_path"]).exists()]
    if len(valid) != len(records):
        _save_registry(user_id, valid)
    return list(reversed(valid))


async def delete_upload(user_id: str, file_id: str) -> None:
    """Delete a file from disk and remove it from the registry."""
    records = _load_registry(user_id)
    target = next((r for r in records if r["file_id"] == file_id), None)

    if not target:
        raise HTTPException(status_code=404, detail="File not found.")
    if target["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Remove from disk
    path = Path(target["storage_path"])
    if path.exists():
        path.unlink()

    # Remove from registry
    updated = [r for r in records if r["file_id"] != file_id]
    _save_registry(user_id, updated)