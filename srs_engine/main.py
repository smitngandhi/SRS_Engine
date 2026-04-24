from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.adk.sessions import InMemorySessionService
from starlette.middleware.sessions import SessionMiddleware
try:
    from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
except ImportError:
    # Safe fallback if middleware path varies
    ProxyHeadersMiddleware = None

from srs_engine.core.config import get_settings
from srs_engine.core.db.mongo import init_mongo
from srs_engine.core.logging import get_logger
from srs_engine.core.logging.config import setup_logging
from srs_engine.core.queue.redis_queue import connect_redis, disconnect_redis, get_redis_manager
from srs_engine.core.routers import (
    auth_router,
    contact_router,
    pages_router,
    srs_router,
    upload_router,
    parse_router,
    upgrade_router,
    generated_upgrade_router,
    diagram_router,
    chat_router,
    monitor_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger = get_logger("srs_engine.main")

    # ── MongoDB ────────────────────────────────────────────────────────
    logger.info("Startup | Initializing MongoDB connection")
    await init_mongo(app, settings)

    # ── Redis ──────────────────────────────────────────────────────────
    logger.info("Startup | Connecting to Redis")
    try:
        await connect_redis()
        # Expose the manager on app.state so routers can reach it via
        # request.app.state.redis  (same pattern as session_service)
        app.state.redis = get_redis_manager()
        logger.info("Startup | Redis ready")
    except Exception as exc:
        # Log the error but do NOT crash the app — endpoints that require
        # the queue will fail gracefully and return 503 instead of taking
        # the whole process down.
        logger.error(f"Startup | Redis connection failed | error={exc}")
        app.state.redis = None

    # ── Notification Worker (for Render to send HF emails) ────────────
    from srs_engine.core.queue.notification_worker import run_notification_worker
    asyncio.create_task(run_notification_worker(app))

    # ── SMTP warning ───────────────────────────────────────────────────
    if not all([settings.smtp_host, settings.smtp_username, settings.smtp_password]):
        logger.warning("WARNING: SMTP not configured — users will NOT receive email backups")

    yield

    # ── Shutdown ───────────────────────────────────────────────────────
    logger.info("Shutdown | Disconnecting Redis")
    await disconnect_redis()
    logger.info("Shutdown | SpecForge AI stopped")


def create_app() -> FastAPI:
    load_dotenv(find_dotenv())
    settings = get_settings()

    setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)
    logger = get_logger("srs_engine.main")
    logger.info("Creating SpecForge AI application")

    app = FastAPI(lifespan=lifespan)

    # Enable proxy awareness (Render/Railway/etc)
    if ProxyHeadersMiddleware:
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        same_site="lax",
        https_only=settings.production,
        max_age=86400,  # 24 hours
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
    app.include_router(generated_upgrade_router)
    app.include_router(diagram_router)
    app.include_router(chat_router)
    app.include_router(monitor_router)

    # ── Favicon fallback ──────────────────────────────────────────────
    from fastapi.responses import FileResponse
    import os
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        # Get absolute path to the static folder relative to this file (main.py)
        static_path = os.path.join(os.path.dirname(__file__), "static", "favicon.png")
        return FileResponse(static_path)

    return app


app = create_app()