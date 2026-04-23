from __future__ import annotations

import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from fastapi.concurrency import run_in_threadpool
from srs_engine.core.config import Settings, get_settings
from srs_engine.core.logging import get_logger

logger = get_logger(__name__)

def _send_smtp(settings: Settings, msg: EmailMessage) -> None:
    """Synchronous SMTP send."""
    try:
        # Add a 15-second timeout to prevent hanging
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
            logger.info(f"SMTP | Email successfully sent to {msg['To']}")
    except Exception as e:
        logger.error(f"SMTP error: {e}")
        raise

# ── Verification Email ────────────────────────────────

def _build_verification_email(
    *,
    from_email: str,
    to_email: str,
    otp: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"SpecForge AI Team <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = f"{otp} is your SpecForge verification code"
    
    content = (
        f"Hi there! 👋\n\n"
        f"Thanks for starting your journey with SpecForge AI. To verify your email address and activate your account, please enter the following code on the verification page:\n\n"
        f"👉 {otp}\n\n"
        f"This code will expire in 2 minutes.\n\n"
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"Best,\n"
        f"Smit and Prachi"
    )
    msg.set_content(content)
    return msg

async def send_verification_email(
    *,
    settings: Settings,
    to_email: str,
    otp: str,
) -> None:
    msg = _build_verification_email(
        from_email=settings.smtp_username,
        to_email=to_email,
        otp=otp,
    )
    logger.info(f"Sending verification email to {to_email}")
    await run_in_threadpool(_send_smtp, settings, msg)

# ── Welcome Email ────────────────────────────────────

def _build_welcome_email(
    *,
    from_email: str,
    to_email: str,
    display_name: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"SpecForge AI Team <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = f"Welcome to the family, {display_name}! ✨"
    
    content = (
        f"Hi {display_name}! 👋\n\n"
        f"Welcome to SpecForge AI! We're absolutely thrilled to have you join our community. 🏠✨\n\n"
        f"You now have access to our suite of AI-powered SRS generation and diagramming tools. "
        f"We built this to make software engineering faster and more intuitive for everyone.\n\n"
        f"Feel free to dive in and start your first project! If you ever have questions or just want to say hi, "
        f"simply reply to this email—we read every single one.\n\n"
        f"Let's build something amazing together! 🚀\n\n"
        f"Best,\n"
        f"Smit and Prachi"
    )
    msg.set_content(content)
    return msg

async def send_welcome_email(
    *,
    settings: Settings,
    to_email: str,
    display_name: str,
) -> None:
    msg = _build_welcome_email(
        from_email=settings.smtp_username,
        to_email=to_email,
        display_name=display_name,
    )
    logger.info(f"Sending welcome email to {to_email}")
    await run_in_threadpool(_send_smtp, settings, msg)

# ── Login Notification (Admin) ─────────────────────────

def _build_login_notification(
    *,
    from_email: str,
    to_email: str,
    username: str,
    user_email: str,
    ip_address: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = f"🔔 Login Alert: {username}"
    
    content = (
        f"Admin Alert 🛡️\n\n"
        f"A user has just logged into SpecForge AI.\n\n"
        f"👤 Username: {username}\n"
        f"📧 Email: {user_email}\n"
        f"🌐 IP Address: {ip_address}\n"
        f"⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    )
    msg.set_content(content)
    return msg

async def send_login_notification(
    *,
    settings: Settings,
    username: str,
    user_email: str,
    ip_address: str,
) -> None:
    msg = _build_login_notification(
        from_email=settings.smtp_username,
        to_email=settings.admin_email,
        username=username,
        user_email=user_email,
        ip_address=ip_address,
    )
    logger.info(f"Sending login notification to admin for {username}")
    await run_in_threadpool(_send_smtp, settings, msg)

# ── Contact Us Email ──────────────────────────────────

def _build_contact_message(
    *,
    from_email: str,
    to_email: str,
    name: str,
    user_email: str,
    subject: str,
    message: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = f"Contact Form: {subject}"
    
    content = (
        f"New message from SpecForge Contact Form:\n\n"
        f"Name: {name}\n"
        f"Email: {user_email}\n"
        f"Subject: {subject}\n\n"
        f"Message:\n{message}"
    )
    msg.set_content(content)
    return msg

async def send_contact_email(
    *,
    settings: Settings,
    name: str,
    email: str,
    subject: str,
    message: str,
) -> None:
    msg = _build_contact_message(
        from_email=settings.smtp_username,
        to_email=settings.admin_email,
        name=name,
        user_email=email,
        subject=subject,
        message=message,
    )
    logger.info(f"Sending contact email from {name}")
    await run_in_threadpool(_send_smtp, settings, msg)

# ── Admin Action Email ────────────────────────────────

def _build_admin_action_email(
    *,
    from_email: str,
    to_email: str,
    subject: str,
    message: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"SpecForge AI Team <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = f"SpecForge AI | {subject}"
    
    content = (
        f"Hello,\n\n"
        f"{message}\n\n"
        f"If you have any questions or feel this was an error, please reply to this email.\n\n"
        f"Best regards,\n"
        f"The SpecForge AI Team"
    )
    msg.set_content(content)
    return msg

async def send_admin_action_email(
    *,
    settings: Settings,
    to_email: str,
    subject: str,
    message: str,
) -> None:
    msg = _build_admin_action_email(
        from_email=settings.smtp_username,
        to_email=to_email,
        subject=subject,
        message=message,
    )
    logger.info(f"Sending admin action email to {to_email}")
    await run_in_threadpool(_send_smtp, settings, msg)

# ── Admin Security Alert ──────────────────────────────

def _build_admin_security_alert(
    *,
    from_email: str,
    to_email: str,
    ip_address: str,
    user_agent: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"SpecForge Security <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = "⚠️ SECURITY ALERT: Admin Login Detected"
    
    content = (
        f"🚨 Admin Security Alert\n\n"
        f"An administrative login has just occurred on SpecForge AI.\n\n"
        f"📍 IP Address: {ip_address}\n"
        f"💻 Device: {user_agent}\n"
        f"⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        f"If this was not you, please secure your Google account and rotate your session keys immediately."
    )
    msg.set_content(content)
    return msg

async def send_admin_security_alert(
    *,
    settings: Settings,
    ip_address: str,
    user_agent: str,
) -> None:
    msg = _build_admin_security_alert(
        from_email=settings.smtp_username,
        to_email=settings.admin_email,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    logger.warning(f"SECURITY | Admin login detected from {ip_address}")
    await run_in_threadpool(_send_smtp, settings, msg)

# ── SRS Complete Email ──────────────────────────────

def _build_srs_complete_email(
    *,
    from_email: str,
    to_email: str,
    project_name: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"SpecForge AI Team <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = f"Your SRS is ready! 📄: {project_name}"
    
    content = (
        f"Hi there! 👋\n\n"
        f"Great news! Your SRS document for '{project_name}' has been successfully generated and is ready for download.\n\n"
        f"You can find it in your 'My Documents' section on the dashboard.\n\n"
        f"Happy building! 🚀\n\n"
        f"Best,\n"
        f"Smit and Prachi"
    )
    msg.set_content(content)
    return msg

async def send_srs_complete_email(
    *,
    settings: Settings,
    to_email: str,
    project_name: str,
) -> None:
    msg = _build_srs_complete_email(
        from_email=settings.smtp_username,
        to_email=to_email,
        project_name=project_name,
    )
    logger.info(f"Sending SRS complete email to {to_email} for {project_name}")
    await run_in_threadpool(_send_smtp, settings, msg)
