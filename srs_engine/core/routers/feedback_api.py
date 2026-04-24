from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from srs_engine.core.auth.deps import require_user
from srs_engine.core.db.mongo import get_db
from srs_engine.core.db.feedback_repo import FeedbackRepo
from srs_engine.core.db.user_repo import UserRepo
from pydantic import BaseModel, Field

router = APIRouter()

class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=5, max_length=1000)

@router.post("/api/feedback")
async def submit_feedback(
    data: FeedbackCreate,
    user: dict = Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    repo = FeedbackRepo(db)
    user_id = str(user["_id"])
    
    # Get avatar if exists
    avatar_url = None
    if user.get("avatar_file_id"):
        avatar_url = f"/api/avatar/{user_id}"

    feedback_id = await repo.add_feedback(
        user_id=user_id,
        display_name=user.get("display_name") or user.get("username") or "User",
        email=user.get("email"),
        rating=data.rating,
        comment=data.comment,
        avatar_url=avatar_url
    )
    return {"status": "success", "feedback_id": feedback_id}

@router.get("/api/feedback")
async def get_public_feedback(db: AsyncIOMotorDatabase = Depends(get_db)):
    repo = FeedbackRepo(db)
    return await repo.get_all_feedback(public_only=True)

@router.get("/api/admin/feedback")
async def admin_get_all_feedback(
    user: dict = Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    from srs_engine.core.db.user_repo import UserRepo
    u_repo = UserRepo(db)
    if not await u_repo.is_admin(user.get("email")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    repo = FeedbackRepo(db)
    return await repo.get_all_feedback(public_only=False)

@router.delete("/api/admin/feedback/{feedback_id}")
async def admin_delete_feedback(
    feedback_id: str,
    user: dict = Depends(require_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    from srs_engine.core.db.user_repo import UserRepo
    u_repo = UserRepo(db)
    if not await u_repo.is_admin(user.get("email")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    repo = FeedbackRepo(db)
    success = await repo.delete_feedback(feedback_id)
    if not success:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"status": "success"}
