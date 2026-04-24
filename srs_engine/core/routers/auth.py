from __future__ import annotations

import re
import random
from datetime import datetime, timezone, timedelta
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from srs_engine.core.auth.google_oauth import init_google_oauth
from srs_engine.core.config import get_settings
from srs_engine.core.db.mongo import get_db
from srs_engine.core.db.user_repo import UserRepo
from srs_engine.core.logging import get_logger
from srs_engine.core.services.email_service import (
    send_verification_email,
    send_welcome_email,
    send_login_notification,
    send_admin_security_alert,
)

router = APIRouter()
logger = get_logger(__name__)
oauth = OAuth()

# ── Helpers ────────────────────────────────────────────

def _set_session(request: Request, user: dict[str, Any]) -> None:
    request.session["user_id"] = str(user["_id"])
    request.session["username"] = user.get("username") or user.get("email") or "user"
    request.session["display_name"] = user.get("display_name") or request.session["username"]
    request.session["has_avatar"] = bool(user.get("avatar_file_id"))

def _redirect_error(url: str, msg: str) -> RedirectResponse:
    return RedirectResponse(url=f"{url}?error={msg}", status_code=302)

@router.on_event("startup")
async def _startup_oauth_register():
    settings = get_settings()
    init_google_oauth(oauth, settings)

# ── Auth Routes ────────────────────────────────────────

@router.post("/auth/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    repo = UserRepo(db)
    user = await repo.authenticate_user(username, password)
    if not user:
        return _redirect_error("/login", "Invalid username or password")

    # ── Check if account is active (not revoked) ──
    if not user.get("is_active", True):
        return _redirect_error("/login", "Your account has been deactivated. Please contact support.")

    # ── Check Email Verification ──
    if not user.get("is_verified", False):
        # Store user_id in session for the verification page
        request.session["verify_user_id"] = str(user["_id"])
        return RedirectResponse(url="/verify", status_code=302)

    _set_session(request, user)
    await repo.update_last_login(str(user["_id"]))

    # ── Admin Login Security Alert ──
    settings = get_settings()
    if user.get("email") == settings.admin_email:
        try:
            await send_admin_security_alert(
                settings=settings,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown")
            )
        except Exception as e:
            logger.error(f"Failed admin security alert: {e}")
    else:
        # Standard admin notification
        try:
            await send_login_notification(
                settings=settings,
                username=user.get("username", "unknown"),
                user_email=user.get("email", "unknown"),
                ip_address=request.client.host if request.client else "unknown",
            )
        except Exception as e:
            logger.error(f"Failed to send login notification: {e}")

    return RedirectResponse(url="/home", status_code=302)


@router.post("/auth/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    repo = UserRepo(db)
    
    # ── Check Beta Cap (10 Users) ──
    current_user_count = await repo.count_users()
    if current_user_count >= 10:
        return _redirect_error("/login", "Beta is currently full (10/10 users). Please try again later!")

    # ── Check if email is locked ──
    existing_user = await repo.get_by_email(email)
    if existing_user and existing_user.get("locked_until"):
        locked_until = existing_user["locked_until"]
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < locked_until:
            return _redirect_error("/login", "This email is temporarily locked due to too many OTP attempts. Please try again in 24 hours.")

    # Simple validation
    if not re.match(r"^[a-zA-Z0-9_.-]{3,32}$", username):
        return _redirect_error("/login", "Invalid username format")
    if len(password) < 8:
        return _redirect_error("/login", "Password too short")

    try:
        user_id = await repo.create_local_user(
            username=username,
            password_plain=password,
            email=email,
            display_name=username
        )
        if not user_id:
            return _redirect_error("/login", "Username or Email already exists")

        # ── Generate & Send OTP ──
        otp = f"{random.randint(100000, 999999)}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
        await repo.set_verification_otp(user_id, otp, expires_at)
        
        try:
            await send_verification_email(
                settings=get_settings(),
                to_email=email,
                otp=otp,
            )
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")

        request.session["verify_user_id"] = user_id
        return RedirectResponse(url="/verify", status_code=302)

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return _redirect_error("/login", "Something went wrong")


@router.post("/auth/resend-otp")
async def resend_otp(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = request.session.get("verify_user_id")
    if not user_id:
        return _redirect_error("/login", "Session expired. Please try again.")

    repo = UserRepo(db)
    user = await repo.get_by_id(user_id)
    if not user:
        return _redirect_error("/login", "User not found")

    # ── Check Lockout ──
    if user.get("locked_until"):
        locked_until = user["locked_until"]
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < locked_until:
            return _redirect_error("/verify", "Your account is locked for 24 hours.")

    # ── Check Resend Limit ──
    current_resends = user.get("otp_resend_count", 0)
    if current_resends >= 3:
        # Lock for 24 hours
        lock_until = datetime.now(timezone.utc) + timedelta(hours=24)
        await repo.lock_user(user_id, lock_until)
        request.session.pop("verify_user_id", None) # Clear session
        return _redirect_error("/login", "Too many resend attempts. This email is now locked for 24 hours.")

    # ── Process Resend ──
    otp = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
    
    await repo.set_verification_otp(user_id, otp, expires_at)
    await repo.increment_otp_resend(user_id)
    
    try:
        await send_verification_email(
            settings=get_settings(),
            to_email=user["email"],
            otp=otp,
        )
    except Exception as e:
        logger.error(f"Failed to resend OTP: {e}")
        return _redirect_error("/verify", "Failed to send email. Please try again later.")

    return RedirectResponse(url="/verify?msg=Code resent successfully", status_code=302)


@router.post("/auth/verify")
async def verify_otp(
    request: Request,
    otp: str = Form(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = request.session.get("verify_user_id")
    if not user_id:
        return _redirect_error("/login", "Session expired")

    repo = UserRepo(db)
    user = await repo.get_by_id(user_id)
    if not user:
        return _redirect_error("/login", "User not found")

    if user.get("verification_otp") != otp:
        return _redirect_error("/verify", "Invalid verification code")

    # Check Expiration
    expires_at = user.get("otp_expires_at")
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            return _redirect_error("/login", "Verification code expired")

    await repo.verify_user(user_id)
    request.session.pop("verify_user_id", None)
    
    _set_session(request, user)
    await repo.update_last_login(user_id)

    settings = get_settings()
    
    # ── Security Logic ──
    if user.get("email") == settings.admin_email:
        await send_admin_security_alert(
            settings=settings,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown")
        )
    else:
        # Welcome email (Standard users only)
        try:
            await send_welcome_email(
                settings=settings,
                to_email=user.get("email"),
                display_name=user.get("display_name") or "User",
            )
        except Exception as e:
            logger.error(f"Failed welcome email: {e}")

        # Admin notification
        try:
            await send_login_notification(
                settings=settings,
                username=user.get("display_name", "user"),
                user_email=user.get("email", "unknown"),
                ip_address=request.client.host if request.client else "unknown",
            )
        except Exception as e:
            logger.error(f"Failed admin notification: {e}")

    return RedirectResponse(url="/home", status_code=302)


@router.get("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/home", status_code=302)


# ── Google OAuth ──

@router.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, str(redirect_uri))


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")
        if not userinfo:
            return _redirect_error("/login", "Failed to fetch user info from Google")

        repo = UserRepo(db)
        email = userinfo.get("email")
        settings = get_settings()
        is_admin = email == settings.admin_email

        # ── Check Beta Cap for NEW users ──
        existing = await repo.get_by_email(email)
        if not existing and not is_admin:
            count = await repo.count_users()
            if count >= 10:
                return _redirect_error("/login", "Beta is currently full (10/10 users). Please try again later!")

        user, is_new = await repo.upsert_google_user(
            google_sub=userinfo["sub"],
            email=userinfo.get("email"),
            display_name=userinfo.get("name"),
        )
        
        # ── Check if account is active ──
        if not user.get("is_active", True):
            return _redirect_error("/login", "Your account has been deactivated. Please contact support.")

        _set_session(request, user)
        await repo.update_last_login(str(user["_id"]))

        settings = get_settings()
        
        # ── Admin vs User Logic ──
        if user.get("email") == settings.admin_email:
            try:
                await send_admin_security_alert(
                    settings=settings,
                    ip_address=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get("user-agent", "unknown")
                )
            except Exception as e:
                logger.error(f"Failed Google admin alert: {e}")
        else:
            if is_new:
                try:
                    await send_welcome_email(
                        settings=settings,
                        to_email=user.get("email"),
                        display_name=user.get("display_name") or "User",
                    )
                except Exception as e:
                    logger.error(f"Failed Google welcome email: {e}")

            # Standard admin notification
            try:
                await send_login_notification(
                    settings=settings,
                    username=user.get("display_name", "user"),
                    user_email=user.get("email", "unknown"),
                    ip_address=request.client.host if request.client else "unknown",
                )
            except Exception as e:
                logger.error(f"Failed admin notification: {e}")

        return RedirectResponse(url="/home", status_code=302)

    except Exception as e:
        logger.error(f"Google callback error: {e}")
        return _redirect_error("/login", "Google login failed")
