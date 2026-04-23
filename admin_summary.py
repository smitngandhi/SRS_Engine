from __future__ import annotations

import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from srs_engine.core.config import get_settings
from srs_engine.core.db.job_model import JobStatus

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    
    print("\n" + "="*80)
    print(" SPECFORGE AI - ADMIN USER SUMMARY")
    print("="*80)
    print(f"{'User Email':<35} | {'Joined':<12} | {'SRS Done':<8} | {'Remaining Quota'}")
    print("-"*80)
    
    users_cursor = db.users.find({})
    async for user in users_cursor:
        user_id = str(user["_id"])
        email = user.get("email") or user.get("username") or "Unknown"
        created_at = user.get("created_at")
        joined_str = created_at.strftime("%Y-%m-%d") if created_at else "N/A"
        
        # Count SRS jobs
        srs_done = await db.srs_jobs.count_documents({
            "user_id": user_id, 
            "status": JobStatus.COMPLETED
        })
        
        # Get quota
        quota_doc = await db.user_quotas.find_one({"user_id": user_id}) or {}
        docx_count = quota_doc.get("docx_count", 0)
        docx_limit = 2 # Beta limit
        remaining = max(0, docx_limit - docx_count)
        
        print(f"{email:<35} | {joined_str:<12} | {srs_done:<8} | {remaining} SRS left")
        
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
