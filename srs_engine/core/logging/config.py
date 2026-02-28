from __future__ import annotations

import logging
import logging.config
import logging.handlers
import os
import queue
from datetime import datetime
from pathlib import Path
from threading import Thread

from .async_logger import ContextFilter


def setup_logging(log_dir: str = "./logs", log_level: str = "INFO") -> None:
    """
    Setup async-safe queue-based logging with timestamped directories.
    
    Each time the app starts, creates a new directory:
    logs/2024-02-28_10-45-32/srs_engine.log
    
    Uses QueueHandler for non-blocking logs from agents + QueueListener
    for file I/O in background thread. This prevents file I/O from
    blocking parallel agent execution.
    """
    # Generate timestamp for this run (YYYY-MM-DD_HH-MM-SS format)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    timestamped_log_dir = str(Path(log_dir) / timestamp)
    
    Path(timestamped_log_dir).mkdir(parents=True, exist_ok=True)

    level = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_file = str(Path(timestamped_log_dir) / "srs_engine.log")

    # ============ FORMATTERS ============
    detailed_formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "session_id=%(session_id)s | user_id=%(user_id)s | "
            "agent_id=%(agent_id)s | %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ============ QUEUE-BASED SETUP (FOR AGENTS) ============
    # Create queue for non-blocking logging from parallel agents
    log_queue = queue.Queue(maxsize=10000)

    # Console handler (writes to stdout in real-time, minimal blocking)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(ContextFilter())

    # File handler (runs in background thread via QueueListener)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB per file
        backupCount=5,  # Keep 5 rotated files
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    file_handler.addFilter(ContextFilter())

    # QueueListener runs in background thread (non-blocking for agents)
    queue_listener = logging.handlers.QueueListener(
        log_queue,
        file_handler,
        console_handler,
        respect_handler_level=True,
    )

    # Start queue listener in daemon thread (won't block app startup)
    queue_listener.start()

    # ============ QUEUE HANDLER (FOR AGENTS) ============
    # This is what agents use - extremely fast, just puts to queue
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setLevel(logging.DEBUG)
    queue_handler.addFilter(ContextFilter())

    # ============ CONFIGURE LOGGERS ============
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | %(name)s | "
                    "session_id=%(session_id)s | user_id=%(user_id)s | "
                    "agent_id=%(agent_id)s | %(message)s"
                ),
            },
            "console": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
                ),
            },
        },
        "filters": {
            "context_filter": {
                "()": ContextFilter,
            },
        },
        "handlers": {
            # Queue handler - used by app and agents (non-blocking)
            "queue": {
                "class": "logging.handlers.QueueHandler",
                "queue": log_queue,
            },
            # Console - immediate output for development
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "console",
                "filters": ["context_filter"],
            },
        },
        "loggers": {
            # SRS Engine - Main app logger (uses queue)
            "srs_engine": {
                "handlers": ["queue"],
                "level": "DEBUG",
                "propagate": False,
            },
            # Agent loggers - Use queue for non-blocking
            "srs_engine.agents": {
                "handlers": ["queue"],
                "level": "DEBUG",
                "propagate": False,
            },
            # Service layer - Use queue
            "srs_engine.core.services": {
                "handlers": ["queue"],
                "level": "DEBUG",
                "propagate": False,
            },
            # Uvicorn error logs
            "uvicorn.error": {
                "handlers": ["queue"],
                "level": level,
                "propagate": False,
            },
            # Uvicorn access logs (less verbose, to console only)
            "uvicorn.access": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["queue"],
            "level": level,
        },
    }

    logging.config.dictConfig(logging_config)

    # Store queue listener reference to prevent garbage collection
    # (needed to keep background thread alive)
    _queue_listener = queue_listener

    logger = logging.getLogger("srs_engine.logging.setup")
    logger.info(
        f"Logging initialized | level={level} | log_file={log_file} | "
        f"queue_size=10000 | rotation=10MB×5"
    )

