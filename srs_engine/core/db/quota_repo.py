from __future__ import annotations

"""
core/db/quota_repo.py

User quota management. Enforces beta limits:
  - 2 SRS documents per user (docx_count)
  - 2 diagrams per project (diagram_count)
  - 2 section upgrades per project (upgrade_count)
  - 15 chat queries per user (chat_query_count)
"""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from srs_engine.core.logging import get_logger
from srs_engine.core.config import get_settings

logger = get_logger(__name__)


class QuotaRepo:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def check_quota(
        self,
        user_id: str,
        quota_type: str,
        project_name: str | None = None,
        limit: int = 2,
    ) -> bool:
        """Returns True if the user is within quota."""
        # 0. Fetch user doc to get email and status
        user = await self.db.users.find_one({"_id": ObjectId(user_id) if isinstance(user_id, str) and len(user_id)==24 else user_id})
        
        # 1. Block Revoked Users
        if user and not user.get("is_active", True):
            return False # Strictly block all features
        
        # 2. Check admin bypass via settings and dedicated admins collection
        settings = get_settings()
        if user and user.get("email"):
            if user["email"] == settings.admin_email:
                return True
            admin = await self.db.admins.find_one({"email": user["email"]})
            if admin:
                return True

        doc = await self.db.user_quotas.find_one({"user_id": user_id})
        if not doc:
            return True  # No record yet — user hasn't used anything

        # ── Handle Custom Quotas ──
        # Check for generalized custom limits in the user doc
        limit_to_use = limit
        if user:
            # Try to find a specific custom limit for this quota type (e.g. custom_docx_limit)
            custom_key = f"custom_{quota_type}_limit"
            limit_to_use = user.get(custom_key, limit)
            
            # Fallback for the old 'custom_quota' field if it exists for docx
            if quota_type == "docx_count" and "custom_quota" in user and custom_key not in user:
                limit_to_use = user["custom_quota"]

        if project_name:
            projects = doc.get("projects", {})
            count = projects.get(project_name, {}).get(quota_type, 0)
        else:
            count = doc.get(quota_type, 0)

        return count < limit_to_use

    async def increment_quota(
        self,
        user_id: str,
        quota_type: str,
        project_name: str | None = None,
    ) -> None:
        """
        Increment a quota counter by 1.

        Args:
            user_id:      The user's ID string.
            quota_type:   Counter field name.
            project_name: If set, increments the per-project counter.
        """
        if project_name:
            await self.db.user_quotas.update_one(
                {"user_id": user_id},
                {"$inc": {f"projects.{project_name}.{quota_type}": 1}},
                upsert=True,
            )
        else:
            await self.db.user_quotas.update_one(
                {"user_id": user_id},
                {"$inc": {quota_type: 1}},
                upsert=True,
            )
        logger.debug(
            f"QuotaRepo | Incremented | user_id={user_id} | "
            f"type={quota_type} | project={project_name}"
        )

    async def get_summary(self, user_id: str) -> dict:
        """Return quota summary for the user (for the /api/my-quota endpoint)."""
        # Fetch user doc for email
        user = await self.db.users.find_one({"_id": ObjectId(user_id) if isinstance(user_id, str) and len(user_id)==24 else user_id})
        
        # Admin Bypass via settings and dedicated collection
        settings = get_settings()
        if user and user.get("email"):
            if user["email"] == settings.admin_email:
                return {
                    "docx_count": 0, "docx_limit": 9999,
                    "chat_query_count": 0, "chat_query_limit": 9999,
                    "is_admin": True,
                    "projects": {}
                }
            admin = await self.db.admins.find_one({"email": user["email"]})
            if admin:
                return {
                    "docx_count": 0, "docx_limit": 9999,
                    "chat_query_count": 0, "chat_query_limit": 9999,
                    "is_admin": True,
                    "projects": {}
                }

        doc = await self.db.user_quotas.find_one({"user_id": user_id}) or {}
        
        # Check for custom limits
        docx_limit = user.get("custom_docx_limit", user.get("custom_quota", 2)) if user else 2
        chat_limit = user.get("custom_chat_query_limit", 15) if user else 15
        diag_limit = user.get("custom_diagram_count_limit", 2) if user else 2
        upgrade_limit = user.get("custom_upgrade_count_limit", 2) if user else 2

        return {
            "docx_count": doc.get("docx_count", 0),
            "docx_limit": docx_limit,
            "chat_query_count": doc.get("chat_query_count", 0),
            "chat_query_limit": chat_limit,
            "diag_limit": diag_limit,
            "upgrade_limit": upgrade_limit,
            "is_admin": False,
            "projects": doc.get("projects", {}),
        }
