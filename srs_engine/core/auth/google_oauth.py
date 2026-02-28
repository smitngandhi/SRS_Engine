from __future__ import annotations

from typing import Any

from authlib.integrations.starlette_client import OAuth


def init_google_oauth(oauth: OAuth, settings: Any) -> None:
    """
    Register Google OAuth client if env vars are present.
    """
    if not (settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri):
        return

    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
        redirect_uri=settings.google_redirect_uri,
    )

