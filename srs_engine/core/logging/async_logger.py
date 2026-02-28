"""
Async-safe logging utilities for SRS Engine.

Features:
- Queue-based non-blocking logging for parallel agents
- Context management (session_id, user_id, agent_id)
- Performance timing
- Thread-safe
"""

import asyncio
import contextvars
import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar

# Context variables for structured logging
session_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'session_id', default=None
)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'user_id', default=None
)
agent_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'agent_id', default=None
)
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'request_id', default=None
)


class ContextFilter(logging.Filter):
    """Adds context variables to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = session_id_var.get() or ''
        record.user_id = user_id_var.get() or ''
        record.agent_id = agent_id_var.get() or ''
        record.request_id = request_id_var.get() or ''
        return True


class LogContext:
    """Context manager for setting logging context."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.agent_id = agent_id
        self.request_id = request_id
        self.tokens = []

    def __enter__(self):
        if self.session_id:
            self.tokens.append(session_id_var.set(self.session_id))
        if self.user_id:
            self.tokens.append(user_id_var.set(self.user_id))
        if self.agent_id:
            self.tokens.append(agent_id_var.set(self.agent_id))
        if self.request_id:
            self.tokens.append(request_id_var.set(self.request_id))
        return self

    def __exit__(self, *args):
        for token in reversed(self.tokens):
            session_id_var.set(token)  # Reset to previous value


async def async_log_context(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """Async context manager for setting logging context."""
    if session_id:
        token_session = session_id_var.set(session_id)
    else:
        token_session = None

    if user_id:
        token_user = user_id_var.set(user_id)
    else:
        token_user = None

    if agent_id:
        token_agent = agent_id_var.set(agent_id)
    else:
        token_agent = None

    if request_id:
        token_request = request_id_var.set(request_id)
    else:
        token_request = None

    try:
        yield
    finally:
        if token_session:
            session_id_var.set(token_session)
        if token_user:
            user_id_var.set(token_user)
        if token_agent:
            agent_id_var.set(token_agent)
        if token_request:
            request_id_var.set(token_request)


T = TypeVar('T')


def log_execution_time(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to log function execution time.

    Usage:
        @log_execution_time
        def my_function():
            pass

        @log_execution_time
        async def my_async_function():
            pass
    """
    logger = logging.getLogger(func.__module__)

    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            func_name = func.__qualname__
            logger.debug(f"Starting {func_name}")
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Completed {func_name} | elapsed_time={elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"Failed {func_name} | elapsed_time={elapsed:.2f}s | error={str(e)}"
                )
                raise

        return async_wrapper

    else:

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            func_name = func.__qualname__
            logger.debug(f"Starting {func_name}")
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Completed {func_name} | elapsed_time={elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"Failed {func_name} | elapsed_time={elapsed:.2f}s | error={str(e)}"
                )
                raise

        return sync_wrapper


def get_context_logger(name: str) -> logging.Logger:
    """Get a logger that includes context in all messages."""
    return logging.getLogger(name)


# Helper functions for setting context
def set_session_id(session_id: str) -> None:
    """Set the current session ID for log context."""
    session_id_var.set(session_id)


def set_user_id(user_id: str) -> None:
    """Set the current user ID for log context."""
    user_id_var.set(user_id)


def set_agent_id(agent_id: str) -> None:
    """Set the current agent ID for log context."""
    agent_id_var.set(agent_id)


def set_request_id(request_id: str) -> None:
    """Set the current request ID for log context."""
    request_id_var.set(request_id)


def clear_context() -> None:
    """Clear all context variables."""
    session_id_var.set(None)
    user_id_var.set(None)
    agent_id_var.set(None)
    request_id_var.set(None)
