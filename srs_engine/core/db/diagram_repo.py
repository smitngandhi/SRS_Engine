from __future__ import annotations

"""
core/db/diagram_repo.py

All MongoDB read/write operations for the `diagrams` collection.

Document structure:
  diagram_id     str        UUID - client-facing key
  user_id        str        ObjectId string of the owner
  project_name   str        Linked project name
  diagram_type   str        flowchart | sequence | erd | class | custom
  created_at     datetime
  updated_at     datetime
  versions       list       Each version: {version_id, version_number, prompt, mermaid_code, svg_path, created_at}
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from srs_engine.core.logging import get_logger

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DiagramRepo:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_diagram(
        self,
        user_id: str,
        project_name: str,
        diagram_type: str,
        prompt: str,
        mermaid_code: str,
        svg_path: str,
    ) -> str:
        """Insert a new diagram document and return its diagram_id (UUID string)."""
        diagram_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        now = _now()

        first_version = {
            "version_id": version_id,
            "version_number": 1,
            "prompt": prompt,
            "mermaid_code": mermaid_code,
            "svg_path": svg_path,
            "created_at": now,
        }

        doc = {
            "diagram_id": diagram_id,
            "user_id": user_id,
            "project_name": project_name,
            "diagram_type": diagram_type,
            "created_at": now,
            "updated_at": now,
            "versions": [first_version],
        }

        await self.db.diagrams.insert_one(doc)
        logger.info(
            f"DiagramRepo | Created | diagram_id={diagram_id} | "
            f"user={user_id} | project={project_name}"
        )
        return diagram_id

    async def add_version(
        self,
        user_id: str,
        diagram_id: str,
        prompt: str,
        mermaid_code: str,
        svg_path: str,
    ) -> int:
        """Append a new version to an existing diagram. Returns the new version number."""
        existing = await self.db.diagrams.find_one(
            {"diagram_id": diagram_id, "user_id": user_id}
        )
        if not existing:
            raise ValueError(f"Diagram {diagram_id} not found for user {user_id}")

        next_version = len(existing["versions"]) + 1
        version_id = str(uuid.uuid4())
        now = _now()

        new_version = {
            "version_id": version_id,
            "version_number": next_version,
            "prompt": prompt,
            "mermaid_code": mermaid_code,
            "svg_path": svg_path,
            "created_at": now,
        }

        await self.db.diagrams.update_one(
            {"diagram_id": diagram_id, "user_id": user_id},
            {
                "$push": {"versions": new_version},
                "$set": {"updated_at": now},
            },
        )
        logger.info(
            f"DiagramRepo | Version added | diagram_id={diagram_id} | v{next_version}"
        )
        return next_version

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_diagram(self, user_id: str, diagram_id: str) -> dict[str, Any] | None:
        """Fetch a single diagram by its UUID (scoped to user)."""
        return await self.db.diagrams.find_one(
            {"diagram_id": diagram_id, "user_id": user_id}
        )

    async def list_by_project(
        self, user_id: str, project_name: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return all diagrams for a specific project, newest first."""
        cursor = (
            self.db.diagrams
            .find({"user_id": user_id, "project_name": project_name})
            .sort("updated_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def list_recent(
        self, user_id: str, limit: int = 6
    ) -> list[dict[str, Any]]:
        """Return most-recently updated diagrams for the home dashboard."""
        cursor = (
            self.db.diagrams
            .find({"user_id": user_id})
            .sort("updated_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def list_projects(self, user_id: str) -> list[str]:
        """Return unique project names that have diagrams for this user."""
        result = await self.db.diagrams.distinct("project_name", {"user_id": user_id})
        return sorted(result)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_diagram(self, user_id: str, diagram_id: str) -> bool:
        """Delete a diagram (hard delete). Returns True if deleted."""
        result = await self.db.diagrams.delete_one(
            {"diagram_id": diagram_id, "user_id": user_id}
        )
        deleted = result.deleted_count > 0
        if deleted:
            logger.info(f"DiagramRepo | Deleted | diagram_id={diagram_id}")
        return deleted
