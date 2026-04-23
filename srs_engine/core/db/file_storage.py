from __future__ import annotations

"""
core/db/file_storage.py

MongoDB GridFS file storage — replaces all disk I/O for generated files.
All generated files (DOCX, JSON, SVG) are stored here for persistence
across server restarts and redeployments.

Metadata convention:
    DOCX:          {"type": "docx",         "user_id": "...", "project_name": "..."}
    Sections JSON: {"type": "sections_json", "user_id": "...", "project_name": "..."}
    Meta JSON:     {"type": "meta_json",     "user_id": "...", "project_name": "..."}
    Version DOCX:  {"type": "version_docx",  "user_id": "...", "project_name": "...", "version": 1}
    SVG:           {"type": "svg",           "user_id": "...", "diagram_id": "...",   "version": 1}
"""

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket

from srs_engine.core.logging import get_logger

logger = get_logger(__name__)


class FileStorage:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.bucket = AsyncIOMotorGridFSBucket(db)

    async def save_file(self, data: bytes, filename: str, metadata: dict) -> str:
        """
        Save bytes to GridFS. If a file with the same metadata already exists,
        it is deleted first (overwrite semantics). Returns file_id as string.
        """
        # Delete old version if exists
        query = {f"metadata.{k}": v for k, v in metadata.items()}
        async for f in self.bucket.find(query):
            await self.bucket.delete(f._id)

        file_id = await self.bucket.upload_from_stream(
            filename, data, metadata=metadata
        )
        logger.debug(f"FileStorage | Saved | filename={filename} | metadata={metadata}")
        return str(file_id)

    async def get_file(self, metadata: dict) -> bytes | None:
        """Get file bytes by metadata match."""
        query = {f"metadata.{k}": v for k, v in metadata.items()}
        async for f in self.bucket.find(query):
            stream = await self.bucket.open_download_stream(f._id)
            return await stream.read()
        return None

    async def get_file_by_id(self, file_id_str: str) -> bytes | None:
        """Get file bytes by GridFS ObjectId string."""
        from bson import ObjectId
        try:
            stream = await self.bucket.open_download_stream(ObjectId(file_id_str))
            return await stream.read()
        except Exception:
            return None

    async def list_files(self, metadata_filter: dict) -> list[dict]:
        """List files matching metadata filter."""
        results = []
        query = {f"metadata.{k}": v for k, v in metadata_filter.items()}
        async for f in self.bucket.find(query):
            results.append({
                "file_id":     str(f._id),
                "filename":    f.filename,
                "metadata":    f.metadata,
                "length":      f.length,
                "upload_date": f.upload_date,
            })
        return results

    async def delete_file(self, metadata: dict) -> None:
        """Delete files matching metadata filter."""
        query = {f"metadata.{k}": v for k, v in metadata.items()}
        async for f in self.bucket.find(query):
            await self.bucket.delete(f._id)
            logger.debug(f"FileStorage | Deleted | file_id={f._id}")

    async def delete_file_by_id(self, file_id_str: str) -> None:
        """Delete a single file by its GridFS ObjectId."""
        from bson import ObjectId
        try:
            await self.bucket.delete(ObjectId(file_id_str))
            logger.debug(f"FileStorage | Deleted | file_id={file_id_str}")
        except Exception:
            pass

    # ── JSON Helpers ─────────────────────────────────────────────────────────

    async def save_json(self, data: dict, filename: str, metadata: dict) -> str:
        """Helper to save a dict as JSON bytes."""
        import json
        bytes_data = json.dumps(data, default=str).encode("utf-8")
        return await self.save_file(bytes_data, filename, metadata)

    async def get_json(self, metadata: dict) -> dict | None:
        """Helper to get a dict from JSON bytes."""
        import json
        bytes_data = await self.get_file(metadata)
        if bytes_data:
            return json.loads(bytes_data.decode("utf-8"))
        return None
