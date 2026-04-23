from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class UploadedFileResponse(BaseModel):
    file_id: str
    original_filename: str
    file_type: str          # "pdf" | "docx"
    size_kb: float
    uploaded_at: datetime
    storage_path: str       # relative path, not exposed to client raw
    user_id: str


class UploadListItem(BaseModel):
    file_id: str
    original_filename: str
    file_type: str
    size_kb: float
    uploaded_at: datetime