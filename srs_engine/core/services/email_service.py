from __future__ import annotations

import smtplib
from email.message import EmailMessage

from starlette.concurrency import run_in_threadpool

from srs_engine.core.config import Settings
from srs_engine.core.logging import get_logger

logger = get_logger("srs_engine.core.services.email")


def _build_message(
    *,
    from_email: str,
    to_email: str,
    name: str,
    email: str,
    subject: str,
    message: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = f"[SRS_Engine Contact] {subject}"
    msg["Reply-To"] = email  # ← When admin clicks Reply, goes to user's email

    body = (
        f"New contact form submission:\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Subject: {subject}\n\n"
        f"Message:\n{message}\n"
    )
    msg.set_content(body)
    return msg


def _send_smtp(settings: Settings, msg: EmailMessage) -> None:
    if not (settings.smtp_host and settings.smtp_from_email and settings.smtp_username and settings.smtp_password):
        raise RuntimeError("SMTP settings are not configured")

    host = settings.smtp_host
    port = settings.smtp_port

    if port == 465:
        server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        server.ehlo()
        server.starttls()
        server.ehlo()

    try:
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass


async def send_contact_email(
    *,
    settings: Settings,
    name: str,
    email: str,
    subject: str,
    message: str,
) -> None:
    msg = _build_message(
        from_email=settings.smtp_from_email or settings.smtp_to_email,
        to_email=settings.smtp_to_email,
        name=name,
        email=email,
        subject=subject,
        message=message,
    )

    logger.info("Sending contact email to %s", settings.smtp_to_email)
    await run_in_threadpool(_send_smtp, settings, msg)

