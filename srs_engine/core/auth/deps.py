from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from srs_engine.core.db.user_repo import UserRepo
from srs_engine.core.db.mongo import get_db


async def optional_user(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)) -> dict[str, Any] | None:
    user_id = request.session.get("user_id")  # type: ignore[attr-defined]
    if not user_id:
        return None
    repo = UserRepo(db)
    return await repo.get_by_id(user_id)


async def require_user(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    user_id = request.session.get("user_id")  # type: ignore[attr-defined]
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    repo = UserRepo(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Invalid session")
    return user

