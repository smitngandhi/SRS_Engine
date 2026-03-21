from __future__ import annotations

import re
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from urllib.parse import quote

from srs_engine.core.auth.google_oauth import init_google_oauth
from srs_engine.core.auth.passwords import hash_password, verify_password
from srs_engine.core.config import get_settings
from srs_engine.core.db.mongo import get_db, is_db_available
from srs_engine.core.db.user_repo import UserRepo
from srs_engine.core.logging import get_logger


router = APIRouter()
logger = get_logger("srs_engine.core.routers.auth")

oauth = OAuth()

# ── Validation constants ──────────────────────────────
USERNAME_MIN = 3
USERNAME_MAX = 32
PASSWORD_MIN = 8
PASSWORD_MAX = 72  # bcrypt hard limit
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]+$')
EMAIL_PATTERN    = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$')


def _redirect_error(url: str, message: str) -> RedirectResponse:
    return RedirectResponse(url=f"{url}?error={quote(message)}", status_code=302)


def _validate_username(username: str) -> str | None:
    """Returns error message or None if valid."""
    if len(username) < USERNAME_MIN:
        return f"Username must be at least {USERNAME_MIN} characters."
    if len(username) > USERNAME_MAX:
        return f"Username cannot exceed {USERNAME_MAX} characters."
    if not USERNAME_PATTERN.match(username):
        return "Username can only contain letters, numbers, underscores, dots, and hyphens."
    return None


def _validate_password(password: str) -> str | None:
    """Returns error message or None if valid."""
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if len(password) > PASSWORD_MAX:
        return f"Password cannot exceed {PASSWORD_MAX} characters."
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number."
    return None


def _validate_email(email: str) -> str | None:
    """Returns error message or None if valid."""
    if not email or not email.strip():
        return "Email address is required."
    if not EMAIL_PATTERN.match(email.strip()):
        return "Please enter a valid email address."
    return None


def _set_session(request: Request, user: dict[str, Any]) -> None:
    request.session["user_id"]      = str(user["_id"])
    request.session["username"]     = user.get("username") or user.get("email") or "user"
    request.session["display_name"] = user.get("display_name") or request.session["username"]


@router.on_event("startup")
async def _startup_oauth_register():
    settings = get_settings()
    init_google_oauth(oauth, settings)


# ── Login ─────────────────────────────────────────────
@router.post("/auth/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        # Check if database is available
        if not is_db_available(request):
            return _redirect_error("/login", "Database not available. Please start MongoDB to use authentication.")

        username = username.strip()
        if not username or not password:
            return _redirect_error("/login", "Username and password are required.")

        repo = UserRepo(db)
        user = await repo.get_by_username(username)

        # Don't reveal whether username or password was wrong
        if not user or not user.get("password_hash"):
            return _redirect_error("/login", "Invalid username or password.")

        if not verify_password(password, user["password_hash"]):
            return _redirect_error("/login", "Invalid username or password.")

        await repo.update_last_login(str(user["_id"]))
        _set_session(request, user)
        logger.info(f"User logged in: {username}")
        return RedirectResponse(url="/home", status_code=302)

    except Exception as e:
        logger.error(f"Login error for user '{username}': {e}")
        return _redirect_error("/login", "Something went wrong. Please try again.")


# ── Register ──────────────────────────────────────────
@router.post("/auth/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),          # ← now required, no longer optional
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        # Check if database is available
        if not is_db_available(request):
            return _redirect_error("/login", "Database not available. Please start MongoDB to use authentication.")

        username = username.strip()
        email    = email.strip()

        # ── Validate username ──
        username_error = _validate_username(username)
        if username_error:
            return _redirect_error("/login", username_error)

        # ── Validate email (required) ──
        email_error = _validate_email(email)
        if email_error:
            return _redirect_error("/login", email_error)

        # ── Validate password ──
        password_error = _validate_password(password)
        if password_error:
            return _redirect_error("/login", password_error)

        repo = UserRepo(db)

        # ── Check username uniqueness ──
        try:
            existing = await repo.get_by_username(username)
            if existing:
                return _redirect_error("/login", f"Username '{username}' is already taken.")
        except Exception as e:
            logger.error(f"DB error checking username uniqueness: {e}")
            return _redirect_error("/login", "Could not verify username availability. Please try again.")

        # ── Check email uniqueness ──
        try:
            existing_email = await repo.get_by_email(email)
            if existing_email:
                return _redirect_error("/login", "An account with this email already exists.")
        except Exception as e:
            logger.error(f"DB error checking email uniqueness: {e}")
            return _redirect_error("/login", "Could not verify email availability. Please try again.")

        # ── Hash password ──
        try:
            password_hash = hash_password(password)
        except Exception as e:
            logger.error(f"Password hashing error: {e}")
            return _redirect_error("/login", "Failed to secure password. Please try again.")

        # ── Create user ──
        try:
            user_id = await repo.create_local_user(
                username=username,
                password_hash=password_hash,
                email=email,            # always provided now
                display_name=username,
            )
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return _redirect_error("/login", "Failed to create account. Please try again.")

        user = await repo.get_by_id(user_id)
        if not user:
            return _redirect_error("/login", "Account created but could not load profile. Please log in.")

        _set_session(request, user)
        logger.info(f"New user registered: {username} | email={email}")
        return RedirectResponse(url="/home", status_code=302)

    except Exception as e:
        logger.error(f"Unexpected registration error: {e}")
        return _redirect_error("/login", "Something went wrong. Please try again.")


# ── Logout ────────────────────────────────────────────
@router.get("/auth/logout")
async def logout(request: Request):
    username = request.session.get("username", "unknown")
    request.session.pop("user_id", None)
    request.session.pop("username", None)
    request.session.pop("display_name", None)
    request.session.clear()
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session")
    logger.info(f"User logged out: {username}")
    return response


# ── Google OAuth ──────────────────────────────────────
@router.get("/auth/google/login")
async def google_login(request: Request):
    settings = get_settings()
    if not (settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri):
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    client = oauth.create_client("google")
    if not client:
        raise HTTPException(status_code=500, detail="Google OAuth client not available")

    try:
        return await client.authorize_redirect(request, settings.google_redirect_uri)
    except Exception as e:
        logger.error(f"Google login redirect error: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate Google login")


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    # Check if database is available
    if not is_db_available(request):
        return _redirect_error("/login", "Database not available. Please start MongoDB to use authentication.")

    client = oauth.create_client("google")
    if not client:
        raise HTTPException(status_code=500, detail="Google OAuth client not available")

    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        logger.error(f"Failed to authorize Google access token: {e}")
        return _redirect_error("/login", "Google authentication failed. Please try again.")

    try:
        userinfo_resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", token=token)
        userinfo = userinfo_resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch Google userinfo: {e}")
        return _redirect_error("/login", "Could not retrieve profile from Google.")

    google_sub   = userinfo.get("id")
    email        = userinfo.get("email")
    display_name = userinfo.get("name") or email

    if not google_sub:
        return _redirect_error("/login", "Google did not return a valid user ID.")

    # Google always provides a real email — no null risk here
    if not email:
        return _redirect_error("/login", "Google did not return an email address.")

    try:
        repo = UserRepo(db)
        user = await repo.upsert_google_user(
            google_sub=google_sub,
            email=email,
            display_name=display_name,
        )
        if not user:
            return _redirect_error("/login", "Failed to create Google account. Please try again.")
    except Exception as e:
        logger.error(f"Google upsert error: {e}")
        return _redirect_error("/login", "Database error during Google sign-in.")

    _set_session(request, user)
    logger.info(f"Google user signed in: {email}")
    return RedirectResponse(url="/home", status_code=302)