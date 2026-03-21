from __future__ import annotations

"""
core/db/mongo.py

Initializes the Motor async MongoDB client and stores it on app.state.
Also declares all collection indexes (idempotent — safe to run on every startup).
"""

from typing import Any

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from srs_engine.core.config import Settings
from srs_engine.core.logging import get_logger

logger = get_logger("srs_engine.core.db.mongo")


async def init_mongo(app: Any, settings: Settings) -> None:
    """
    Initialize MongoDB client and store it on app.state.
    Declares indexes for all collections on startup.
    """
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    app.state.mongo_client = client
    app.state.mongo_db = db

    try:
        # ── users ──────────────────────────────────────────────────────
        await db.users.create_index("username", unique=True, sparse=True)
        await db.users.create_index("email", unique=True, sparse=True)
        await db.users.create_index("google_sub", unique=True, sparse=True)

        # ── srs_jobs ───────────────────────────────────────────────────
        # job_id is the client-facing UUID — must be unique and fast to look up
        await db.srs_jobs.create_index("job_id", unique=True)

        # List all jobs for a user, newest first (used by dashboard + SSE)
        await db.srs_jobs.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)]
        )

        # Worker/monitor queries: find all pending or processing jobs
        await db.srs_jobs.create_index("status")

        logger.info("MongoDB | Indexes declared for [users, srs_jobs]")

    except Exception:
        logger.exception("MongoDB | Failed creating indexes")


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.mongo_db  # type: ignore[attr-defined]