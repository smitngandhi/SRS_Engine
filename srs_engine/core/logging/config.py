from __future__ import annotations

import logging
import logging.config
import logging.handlers
import os
import queue
from datetime import datetime
from pathlib import Path

from .async_logger import ContextFilter


def setup_logging(log_dir: str = "./logs", log_level: str = "INFO") -> None:
    """
    Setup async-safe queue-based logging with daily log files.

    All runs on the same day append to the same file:
        logs/2024-02-28/srs_engine.log

    Uses QueueHandler for non-blocking logs from agents + QueueListener
    for file I/O in background thread. This prevents file I/O from
    blocking parallel agent execution.
    """
    # One folder per day — all runs that day append to the same file
    date_str = datetime.now().strftime("%Y-%m-%d")
    daily_log_dir = Path(log_dir) / date_str
    daily_log_dir.mkdir(parents=True, exist_ok=True)

    level = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_file = str(daily_log_dir / "srs_engine.log")

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
    log_queue = queue.Queue(maxsize=10000)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(ContextFilter())

    # 'a' mode (default) — appends to existing file, never overwrites
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        mode="a",                   # append — all runs stack into one file
        maxBytes=50 * 1024 * 1024,  # 50 MB before rotating (bigger since multiple runs)
        backupCount=7,              # keep 7 rotated files (~one week)
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    file_handler.addFilter(ContextFilter())

    queue_listener = logging.handlers.QueueListener(
        log_queue,
        file_handler,
        console_handler,
        respect_handler_level=True,
    )
    queue_listener.start()

    # ============ QUEUE HANDLER (FOR AGENTS) ============
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
            "queue": {
                "class": "logging.handlers.QueueHandler",
                "queue": log_queue,
            },
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "console",
                "filters": ["context_filter"],
            },
        },
        "loggers": {
            "srs_engine": {
                "handlers": ["queue"],
                "level": "DEBUG",
                "propagate": False,
            },
            "srs_engine.agents": {
                "handlers": ["queue"],
                "level": "DEBUG",
                "propagate": False,
            },
            "srs_engine.core.services": {
                "handlers": ["queue"],
                "level": "DEBUG",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["queue"],
                "level": level,
                "propagate": False,
            },
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

    # Prevent garbage collection of listener (keeps background thread alive)
    global _queue_listener
    _queue_listener = queue_listener

    logger = logging.getLogger("srs_engine.logging.setup")
    logger.info(
        f"Logging initialized | level={level} | log_file={log_file} | "
        f"queue_size=10000 | rotation=50MB×7"
    )


# Module-level reference to prevent GC
_queue_listener: logging.handlers.QueueListener | None = None