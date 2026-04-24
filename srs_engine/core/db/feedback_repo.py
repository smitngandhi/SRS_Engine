from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict, Any

class FeedbackRepo:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def add_feedback(self, user_id: str, display_name: str, email: str, rating: int, comment: str, avatar_url: str | None = None) -> str:
        doc = {
            "user_id": user_id,
            "display_name": display_name,
            "email": email,
            "rating": rating,
            "comment": comment,
            "avatar_url": avatar_url,
            "created_at": datetime.now(timezone.utc),
            "is_public": True
        }
        res = await self.db.feedback.insert_one(doc)
        return str(res.inserted_id)

    async def get_all_feedback(self, public_only: bool = False) -> List[Dict[str, Any]]:
        query = {"is_public": True} if public_only else {}
        cursor = self.db.feedback.find(query).sort("created_at", -1)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results

    async def delete_feedback(self, feedback_id: str) -> bool:
        try:
            oid = ObjectId(feedback_id)
            res = await self.db.feedback.delete_one({"_id": oid})
            return res.deleted_count > 0
        except:
            return False

    async def set_visibility(self, feedback_id: str, is_public: bool) -> bool:
        try:
            oid = ObjectId(feedback_id)
            res = await self.db.feedback.update_one({"_id": oid}, {"$set": {"is_public": is_public}})
            return res.modified_count > 0
        except:
            return False
