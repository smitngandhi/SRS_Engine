from __future__ import annotations

from typing import Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from srs_engine.core.db.job_model import JobStatus

def format_ts(dt: Any) -> str:
    """Helper to format datetime into relative 'time ago' string."""
    from datetime import datetime, timezone
    if not dt: return "Never"
    
    # Ensure dt is a datetime object
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
            
    # Ensure dt is timezone-aware (assume UTC if not specified)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    now = datetime.now(timezone.utc)
    diff = now - dt
    
    # Calculate IST time (UTC + 5:30)
    from datetime import timedelta
    ist_time = dt + timedelta(hours=5, minutes=30)
    clock_str = ist_time.strftime("%I:%M %p")
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return f"Just now ({clock_str})"
    elif seconds < 3600:
        mins = int(seconds // 60)
        return f"{mins}m ago ({clock_str})"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours}h ago ({clock_str})"
    else:
        days = int(seconds // 86400)
        if days == 1: return f"Yesterday ({clock_str})"
        return ist_time.strftime("%b %d, %I:%M %p")

class TrackingService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_user_progress(self, user_id: str) -> dict[str, Any]:
        """
        Calculates the progress of a user's most recent job.
        Returns a percentage and the current step.
        """
        # Find the most recent job for this user
        job = await self.db.jobs.find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        )
        
        if not job:
            return {"progress": 0, "status": "No active projects"}

        status = job.get("status")
        if status == JobStatus.COMPLETED:
            return {"progress": 100, "status": "Completed"}
        elif status == JobStatus.FAILED:
            return {"progress": 0, "status": "Failed"}
        
        # Estimate progress based on internal state if available
        # (This is a simplified version)
        steps_completed = job.get("steps_completed", 0)
        total_steps = job.get("total_steps", 5) # Default assumption
        
        pct = min(round((steps_completed / total_steps) * 100), 95)
        return {"progress": pct, "status": status}

    async def get_admin_stats(self, admin_email: str = "hello.specforge@gmail.com") -> dict[str, Any]:
        """
        Aggregates deep stats for the admin dashboard, including user quotas and history.
        """
        total_users = await self.db.users.count_documents({"email": {"$ne": admin_email}})
        total_jobs = await self.db.jobs.count_documents({})
        active_jobs = await self.db.jobs.count_documents({"status": {"$in": [JobStatus.PENDING, JobStatus.PROCESSING]}})
        completed_jobs = await self.db.jobs.count_documents({"status": JobStatus.COMPLETED})

        # Get all non-admin users to show detailed tracking
        cursor = self.db.users.find(
            {"email": {"$ne": admin_email}}, 
            sort=[("last_login_at", -1)]
        ).limit(20)
        
        user_metrics = []
        async for u in cursor:
            u_id = str(u["_id"])
            # Get user's job stats
            u_jobs_cursor = self.db.jobs.find({"user_id": u_id}, sort=[("created_at", -1)]).limit(3)
            recent_jobs = []
            async for j in u_jobs_cursor:
                recent_jobs.append({
                    "name": j.get("project_name", "Untitled"),
                    "status": j.get("status"),
                    "created": format_ts(j.get("created_at"))
                })
            
            job_count = await self.db.jobs.count_documents({"user_id": u_id})

            # ── NEW: Fetch Full Quota Info ──
            quota_doc = await self.db.user_quotas.find_one({"user_id": u_id}) or {}

            projects_data = quota_doc.get("projects", {})
            if isinstance(projects_data, dict):
                project_list = list(projects_data.values())
            else:
                project_list = projects_data if isinstance(projects_data, list) else []

            user_metrics.append({
                "id": u_id,
                "email": u.get("email", "unknown"),
                "display_name": u.get("display_name", "User"),
                "joined": format_ts(u.get("created_at")),
                "last_login": format_ts(u.get("last_login_at")),
                "job_count": job_count,
                "recent_jobs": recent_jobs,
                "is_verified": u.get("is_verified", False),
                "is_active": u.get("is_active", True),
                # Quota Breakdown
                "quotas": {
                    "srs": {"used": quota_doc.get("docx_count", 0), "limit": u.get("custom_docx_limit") or u.get("custom_quota") or 2},
                    "chat": {"used": quota_doc.get("chat_query_count", 0), "limit": u.get("custom_chat_query_limit") or 15},
                    "diagrams": {"used": sum([p.get("diagram_count", 0) for p in project_list if isinstance(p, dict)]), "limit": u.get("custom_diagram_count_limit") or 2},
                    "upgrades": {"used": sum([p.get("upgrade_count", 0) for p in project_list if isinstance(p, dict)]), "limit": u.get("custom_upgrade_count_limit") or 2}
                }
            })

        return {
            "total_users": total_users,
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "user_metrics": user_metrics
        }
