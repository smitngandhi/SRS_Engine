from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserRepo:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None
        return await self.db.users.find_one({"_id": oid})

    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        return await self.db.users.find_one({"username": username})

    async def get_by_google_sub(self, google_sub: str) -> dict[str, Any] | None:
        return await self.db.users.find_one({"google_sub": google_sub})

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        return await self.db.users.find_one({"email": email})

    async def create_local_user(
        self,
        username: str,
        password_hash: str,
        email: str | None = None,
        display_name: str | None = None,
    ) -> str:
        doc = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "google_sub": None,
            "display_name": display_name or username,
            "is_active": True,
            "created_at": _now(),
            "last_login_at": None,
        }
        result = await self.db.users.insert_one(doc)
        return str(result.inserted_id)

    async def upsert_google_user(
        self,
        google_sub: str,
        email: str | None,
        display_name: str | None,
    ) -> dict[str, Any]:
        # Look up by google_sub first, then fall back to email.
        # This prevents a duplicate-key error when a user already exists with
        # the same email but a missing or different google_sub.
        existing = await self.db.users.find_one({"google_sub": google_sub})
        if not existing and email:
            existing = await self.db.users.find_one({"email": email})

        if existing:
            # Update the existing document — never risk inserting a duplicate.
            await self.db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "google_sub": google_sub,
                    "email": email,
                    "display_name": display_name or email or "Google User",
                    "last_login_at": _now(),
                    "is_active": True,
                }},
            )
            return await self.db.users.find_one({"_id": existing["_id"]})

        # Brand-new user — safe to insert.
        doc = {
            "google_sub": google_sub,
            "email": email,
            "display_name": display_name or email or "Google User",
            "username": None,
            "password_hash": None,
            "is_active": True,
            "created_at": _now(),
            "last_login_at": _now(),
        }
        result = await self.db.users.insert_one(doc)
        return await self.db.users.find_one({"_id": result.inserted_id})

    async def update_last_login(self, user_id: str) -> None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return
        await self.db.users.update_one({"_id": oid}, {"$set": {"last_login_at": _now()}})