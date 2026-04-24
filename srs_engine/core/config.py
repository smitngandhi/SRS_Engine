from __future__ import annotations

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

def _env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ── App Core ──────────────────────────────────────────
    session_secret_key: str = _env("SESSION_SECRET_KEY", "dev_secret_key") or "dev_secret_key"
    max_beta_users: int = 10
    
    # ── Logging ───────────────────────────────────────────
    log_dir: str = _env("LOG_DIR", "logs") or "logs"
    log_level: str = _env("LOG_LEVEL", "INFO") or "INFO"
    
    # ── Database ──────────────────────────────────────────
    mongodb_uri: str = _env("MONGODB_URI", "mongodb://localhost:27017") or "mongodb://localhost:27017"
    mongodb_db: str = _env("MONGODB_DB", "specforgeai") or "specforgeai"
    
    # ── Queue ─────────────────────────────────────────────
    redis_url: str = _env("REDIS_URL", "redis://localhost:6379") or "redis://localhost:6379"
    redis_queue_name: str = _env("REDIS_QUEUE_NAME", "srs_queue") or "srs_queue"
    
    # ── AI / Groq ─────────────────────────────────────────
    groq_api_key: str = _env("GROQ_API_KEY", "") or ""
    
    # ── SMTP / Email ──────────────────────────────────────
    smtp_host: str = _env("SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com"
    smtp_port: int = int(_env("SMTP_PORT", "587") or 587)
    smtp_username: str = _env("SMTP_USERNAME", "") or ""
    smtp_password: str = _env("SMTP_PASSWORD", "") or ""
    smtp_from_email: str = _env("SMTP_FROM_EMAIL", "") or ""
    smtp_to_email: str = _env("SMTP_TO_EMAIL", "hello.specforge@gmail.com") or "hello.specforge@gmail.com"
    
    # ── Google OAuth ──────────────────────────────────────
    google_oauth_client_id: str = _env("GOOGLE_OAUTH_CLIENT_ID", "") or ""
    google_oauth_client_secret: str = _env("GOOGLE_OAUTH_CLIENT_SECRET", "") or ""
    google_oauth_redirect_uri: str = _env("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/google/callback") or "http://localhost:8000/auth/google/callback"
    
    # ── Admin Settings ────────────────────────────────────
    admin_email: str = "hello.specforge@gmail.com"
    
    # Production mode
    production: bool = (_env("PRODUCTION", "false") or "false").lower() == "true"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
