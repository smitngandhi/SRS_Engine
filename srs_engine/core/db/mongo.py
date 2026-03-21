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
    try:
        client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        # Test connection
        await client.admin.command('ping')
        
        db = client[settings.mongodb_db]

        app.state.mongo_client = client
        app.state.mongo_db = db

        # Ensure indexes (idempotent)
        try:
            await db.users.create_index("username", unique=True, sparse=True)
            await db.users.create_index("email", unique=True, sparse=True)
            await db.users.create_index("google_sub", unique=True, sparse=True)
            logger.info("MongoDB initialized successfully with indexes")
        except Exception as e:
            logger.warning(f"Failed creating MongoDB indexes: {e}")
            
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        logger.warning("Application will continue without MongoDB. Some features may not work.")
        # Set None values so the app can continue
        app.state.mongo_client = None
        app.state.mongo_db = None


def get_db(request: Request) -> AsyncIOMotorDatabase:
    """Get MongoDB database instance. Returns None if MongoDB is not available."""
    return request.app.state.mongo_db  # type: ignore[attr-defined]


def is_db_available(request: Request) -> bool:
    """Check if MongoDB is available."""
    return request.app.state.mongo_db is not None


# TEMPORARY: Mock database functions for testing without MongoDB
async def mock_get_db(request: Request) -> AsyncIOMotorDatabase:
    """Mock database function for testing without MongoDB."""
    return None

