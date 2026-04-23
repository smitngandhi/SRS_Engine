from __future__ import annotations

from typing import Any

from authlib.integrations.starlette_client import OAuth


def init_google_oauth(oauth: OAuth, settings: Any) -> None:
    """
    Register Google OAuth client if env vars are present.
    """
    client_id = settings.google_oauth_client_id
    client_secret = settings.google_oauth_client_secret
    redirect_uri = settings.google_oauth_redirect_uri

    if not (client_id and client_secret):
        from srs_engine.core.logging import get_logger
        logger = get_logger(__name__)
        logger.warning(
            f"Google OAuth NOT registered. Missing credentials. "
            f"ID_LEN={len(client_id) if client_id else 0}, "
            f"SECRET_LEN={len(client_secret) if client_secret else 0}"
        )
        return

    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
        redirect_uri=redirect_uri,
    )

