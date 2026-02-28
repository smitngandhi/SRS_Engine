from __future__ import annotations

from typing import Any

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from srs_engine.core.config import Settings
from srs_engine.core.logging import get_logger

logger = get_logger("srs_engine.core.db.mongo")


async def init_mongo(app: Any, settings: Settings) -> None:
    """
    Initialize MongoDB client and store it on app.state.
    """
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    app.state.mongo_client = client
    app.state.mongo_db = db

    # Ensure indexes (idempotent)
    try:
        await db.users.create_index("username", unique=True, sparse=True)
        await db.users.create_index("email", unique=True, sparse=True)
        await db.users.create_index("google_sub", unique=True, sparse=True)
    except Exception:
        logger.exception("Failed creating MongoDB indexes")


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.mongo_db  # type: ignore[attr-defined]

