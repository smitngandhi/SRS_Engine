from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


def _env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    if val is None:
        return default
    return val


@dataclass(frozen=True)
class Settings:
    # Sessions
    session_secret_key: str = _env("SESSION_SECRET_KEY", "dev-insecure-change-me") or "dev-insecure-change-me"

    # Mongo
    mongodb_uri: str = _env("MONGODB_URI", "mongodb://localhost:27017") or "mongodb://localhost:27017"
    mongodb_db: str = _env("MONGODB_DB", "srs_engine") or "srs_engine"

    # Google OAuth
    google_client_id: str | None = _env("GOOGLE_OAUTH_CLIENT_ID")
    google_client_secret: str | None = _env("GOOGLE_OAUTH_CLIENT_SECRET")
    google_redirect_uri: str | None = _env("GOOGLE_OAUTH_REDIRECT_URI")

    # SMTP
    smtp_host: str | None = _env("SMTP_HOST")
    smtp_port: int = int(_env("SMTP_PORT", "587") or "587")
    smtp_username: str | None = _env("SMTP_USERNAME")
    smtp_password: str | None = _env("SMTP_PASSWORD")
    smtp_from_email: str | None = _env("SMTP_FROM_EMAIL")
    smtp_to_email: str = _env("SMTP_TO_EMAIL", "smitgandhi585@gmail.com") or "smitgandhi585@gmail.com"

    # Logging
    log_level: str = (_env("LOG_LEVEL", "INFO") or "INFO").upper()
    log_dir: str = _env("LOG_DIR", "./logs") or "./logs"

    # RabbitMQ
    rabbitmq_host: str = _env("RABBITMQ_HOST", "localhost") or "localhost"
    rabbitmq_port: int = int(_env("RABBITMQ_PORT", "5672") or "5672")
    rabbitmq_user: str = _env("RABBITMQ_USER", "guest") or "guest"
    rabbitmq_password: str = _env("RABBITMQ_PASSWORD", "guest") or "guest"
    rabbitmq_vhost: str = _env("RABBITMQ_VHOST", "/") or "/"
    rabbitmq_srs_queue: str = _env("RABBITMQ_SRS_QUEUE", "srs_generation") or "srs_generation"


def get_settings() -> Settings:
    return Settings()