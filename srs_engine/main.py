from __future__ import annotations

"""
SRS_Engine FastAPI entrypoint.

This module was refactored to register routers from `srs_engine/core/routers/`,
set up centralized logging, configure MongoDB, and enable cookie sessions.

The legacy monolithic implementation is preserved below (disabled) to avoid
deleting existing code while keeping runtime behavior clean and production-ready.
"""

from contextlib import asynccontextmanager
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.adk.sessions import InMemorySessionService
from starlette.middleware.sessions import SessionMiddleware

from srs_engine.core.config import get_settings
from srs_engine.core.db.mongo import init_mongo
from srs_engine.core.logging import get_logger
from srs_engine.core.logging.config import setup_logging
from srs_engine.core.routers import auth_router, contact_router, pages_router, srs_router , upload_router, parse_router , upgrade_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB
    settings = get_settings()
    logger = get_logger("srs_engine.main")
    logger.info("Initializing MongoDB connection")
    await init_mongo(app, settings)
    yield
    # Shutdown: Cleanup if needed
    logger.info("Shutting down SRS_Engine")


def create_app() -> FastAPI:
    load_dotenv(find_dotenv())
    settings = get_settings()

    setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)
    logger = get_logger("srs_engine.main")
    logger.info("Starting SRS_Engine")

    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        same_site="lax",
        https_only=False,
    )

    app.mount("/static", StaticFiles(directory="srs_engine/static"), name="static")

    app.state.templates = Jinja2Templates(directory="srs_engine/templates")
    app.state.session_service_stateful = InMemorySessionService()

    app.include_router(pages_router)
    app.include_router(auth_router)
    app.include_router(srs_router)
    app.include_router(contact_router)
    app.include_router(upload_router)
    app.include_router(parse_router)
    app.include_router(upgrade_router)

    return app


app = create_app()