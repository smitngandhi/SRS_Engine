from __future__ import annotations

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
from srs_engine.core.queue.rabbitmq import connect_rabbitmq, disconnect_rabbitmq, get_rabbitmq_manager
from srs_engine.core.routers import (
    auth_router,
    contact_router,
    pages_router,
    srs_router,
    upload_router,
    parse_router,
    upgrade_router,
    diagram_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger = get_logger("srs_engine.main")

    # ── MongoDB ────────────────────────────────────────────────────────
    logger.info("Startup | Initializing MongoDB connection")
    await init_mongo(app, settings)

    # ── RabbitMQ ───────────────────────────────────────────────────────
    logger.info("Startup | Connecting to RabbitMQ")
    try:
        await connect_rabbitmq()
        # Expose the manager on app.state so routers can reach it via
        # request.app.state.rabbitmq  (same pattern as session_service)
        app.state.rabbitmq = get_rabbitmq_manager()
        logger.info("Startup | RabbitMQ ready")
    except Exception as exc:
        # Log the error but do NOT crash the app — endpoints that require
        # the queue will fail gracefully and return 503 instead of taking
        # the whole process down.
        logger.error(f"Startup | RabbitMQ connection failed | error={exc}")
        app.state.rabbitmq = None

    yield

    # ── Shutdown ───────────────────────────────────────────────────────
    logger.info("Shutdown | Disconnecting RabbitMQ")
    await disconnect_rabbitmq()
    logger.info("Shutdown | SRS_Engine stopped")


def create_app() -> FastAPI:
    load_dotenv(find_dotenv())
    settings = get_settings()

    setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)
    logger = get_logger("srs_engine.main")
    logger.info("Creating SRS_Engine application")

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
    app.include_router(diagram_router)

    return app


app = create_app()