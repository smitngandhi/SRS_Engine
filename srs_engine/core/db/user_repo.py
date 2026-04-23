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
        
        # Check users first (99% of cases)
        user = await self.db.users.find_one({"_id": oid})
        if user:
            return user
            
        # Check admins collection
        admin = await self.db.admins.find_one({"_id": oid})
        if admin:
            admin["role"] = "admin" # Ensure role is present for logic
            return admin
            
        return None

    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        return await self.db.users.find_one({"username": username})

    async def get_by_google_sub(self, google_sub: str) -> dict[str, Any] | None:
        return await self.db.users.find_one({"google_sub": google_sub})

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        return await self.db.users.find_one({"email": email})

    async def is_admin(self, email: str) -> bool:
        """Check if an email is registered in the dedicated admins collection or is the primary config admin."""
        from srs_engine.core.config import get_settings
        if email == get_settings().admin_email:
            return True
        admin = await self.db.admins.find_one({"email": email})
        return admin is not None

    async def create_local_user(
        self,
        username: str,
        password_plain: str,
        email: str | None = None,
        display_name: str | None = None,
    ) -> str:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password_hash = pwd_context.hash(password_plain)

        # Admin check against dedicated collection
        is_admin = await self.is_admin(email) if email else False

        doc = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "display_name": display_name or username,
            "role": "admin" if is_admin else "user",
            "is_active": True,
            "custom_docx_limit": 2,
            "is_verified": False,
            "verification_otp": None,
            "otp_expires_at": None,
            "otp_resend_count": 0,
            "locked_until": None,
            "created_at": _now(),
            "last_login_at": None,
        }
        from pymongo.errors import DuplicateKeyError
        try:
            result = await self.db.users.insert_one(doc)
            return str(result.inserted_id)
        except DuplicateKeyError:
            return None

    async def set_verification_otp(self, user_id: str, otp: str, expires_at: datetime) -> None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return
        await self.db.users.update_one(
            {"_id": oid}, 
            {"$set": {"verification_otp": otp, "otp_expires_at": expires_at}}
        )

    async def verify_user(self, user_id: str) -> None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return
        await self.db.users.update_one(
            {"_id": oid}, 
            {"$set": {
                "is_verified": True, 
                "verification_otp": None, 
                "otp_expires_at": None,
                "otp_resend_count": 0,
                "locked_until": None
            }}
        )

    async def increment_otp_resend(self, user_id: str) -> int:
        """Increment resend count and return the NEW count."""
        try:
            oid = ObjectId(user_id)
        except Exception:
            return 0
        result = await self.db.users.find_one_and_update(
            {"_id": oid},
            {"$inc": {"otp_resend_count": 1}},
            return_document=True
        )
        return result.get("otp_resend_count", 0) if result else 0

    async def lock_user(self, user_id: str, until: datetime) -> None:
        """Lock the user account until a specific time."""
        try:
            oid = ObjectId(user_id)
        except Exception:
            return
        await self.db.users.update_one(
            {"_id": oid},
            {"$set": {"locked_until": until}}
        )

    async def upsert_google_user(
        self,
        google_sub: str,
        email: str | None,
        display_name: str | None,
    ) -> tuple[dict[str, Any], bool]:
        """Upsert user into either 'admins' or 'users' collection based on identity."""
        
        # 1. Determine target collection
        is_admin = await self.is_admin(email) if email else False
        target_coll = self.db.admins if is_admin else self.db.users
        
        # 2. Look up existing in target
        existing = await target_coll.find_one({"google_sub": google_sub})
        if not existing and email:
            existing = await target_coll.find_one({"email": email})

        if existing:
            await target_coll.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "google_sub": google_sub,
                    "email": email,
                    "display_name": display_name or email or "User",
                    "last_login_at": _now(),
                    "is_active": True,
                }},
            )
            return await target_coll.find_one({"_id": existing["_id"]}), False

        # 3. Create brand-new record
        doc = {
            "google_sub": google_sub,
            "email": email,
            "display_name": display_name or email or "User",
            "password_hash": None,
            "is_active": True,
            "is_verified": True,
            "role": "admin" if is_admin else "user",
            "created_at": _now(),
            "last_login_at": _now(),
        }
        
        if not is_admin:
            doc["custom_docx_limit"] = 2
            doc["custom_chat_query_limit"] = 15

        res = await target_coll.insert_one(doc)
        return await target_coll.find_one({"_id": res.inserted_id}), True

    async def update_last_login(self, user_id: str) -> None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return
        await self.db.users.update_one({"_id": oid}, {"$set": {"last_login_at": _now()}})

    async def count_users(self) -> int:
        """Return the total number of registered users (for beta cap enforcement)."""
        return await self.db.users.count_documents({})

    async def authenticate_user(self, username: str, password_plain: str) -> dict[str, Any] | None:
        """
        Verify credentials for a local user.
        Uses bcrypt for secure password hashing.
        """
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Find by username OR email
        user = await self.db.users.find_one({
            "$or": [
                {"username": username},
                {"email": username}
            ]
        })
        if not user or not user.get("password_hash"):
            return None

        if not pwd_context.verify(password_plain, user["password_hash"]):
            return None

        return user

    async def set_active_status(self, user_id: str, active: bool) -> None:
        """Revoke or restore user access."""
        try:
            oid = ObjectId(user_id)
        except Exception:
            return
        await self.db.users.update_one({"_id": oid}, {"$set": {"is_active": active}})

    async def update_all_quotas(self, user_id: str, srs_limit: int, chat_limit: int, diag_limit: int, upgrade_limit: int) -> None:
        """Global promotion across all platform features."""
        try:
            oid = ObjectId(user_id)
        except Exception:
            return
        await self.db.users.update_one(
            {"_id": oid}, 
            {"$set": {
                "custom_docx_limit": srs_limit,
                "custom_chat_query_limit": chat_limit,
                "custom_diagram_count_limit": diag_limit,
                "custom_upgrade_count_limit": upgrade_limit,
                "is_promoted": True
            }}
        )

    async def get_quota_status(self, user_id: str) -> dict[str, Any]:
        """Check user role and quota usage."""
        user = await self.get_by_id(user_id)
        if not user:
            return {"allowed": False, "reason": "User not found"}
        
        if user.get("role") == "admin":
            return {"allowed": True, "reason": "Admin privilege", "unlimited": True}
        
        limit = user.get("custom_quota", 2)
        used = await self.db.jobs.count_documents({"user_id": user_id})
        
        return {
            "allowed": used < limit,
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used)
        }