from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from srs_engine.core.db.user_repo import UserRepo
from srs_engine.core.db.mongo import get_db, is_db_available, mock_get_db


async def optional_user(request: Request, db: AsyncIOMotorDatabase = Depends(mock_get_db)) -> dict[str, Any] | None:
    # TEMPORARY: Return mock user for testing without authentication
    return {
        "_id": "test_user_id",
        "username": "test_user",
        "display_name": "Test User",
        "email": "test@example.com",
        "is_active": True
    }
    
    # Original code (commented out for testing)
    # user_id = request.session.get("user_id")  # type: ignore[attr-defined]
    # if not user_id:
    #     return None
    # 
    # # Check if database is available
    # if not is_db_available(request):
    #     return None
    # 
    # repo = UserRepo(db)
    # return await repo.get_by_id(user_id)


async def require_user(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(mock_get_db),
) -> dict[str, Any]:
    # TEMPORARY: Return mock user for testing without authentication
    return {
        "_id": "test_user_id",
        "username": "test_user",
        "display_name": "Test User",
        "email": "test@example.com",
        "is_active": True
    }
    
    # Original code (commented out for testing)
    # # Check if database is available
    # if not is_db_available(request):
    #     raise HTTPException(status_code=503, detail="Database not available. Please start MongoDB to use authentication.")
    # 
    # user_id = request.session.get("user_id")  # type: ignore[attr-defined]
    # if not user_id:
    #     raise HTTPException(status_code=401, detail="Authentication required")
    # repo = UserRepo(db)
    # user = await repo.get_by_id(user_id)
    # if not user or not user.get("is_active", True):
    #     raise HTTPException(status_code=401, detail="Invalid session")
    # return user

