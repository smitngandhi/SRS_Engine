from __future__ import annotations

"""
core/services/email_service.py

send_srs_complete_email() now attaches the generated .docx file directly
instead of sending a download link. The file is read from disk inside
run_in_threadpool so the async worker is never blocked.
"""

import smtplib
from email.message import EmailMessage
from pathlib import Path

from starlette.concurrency import run_in_threadpool

from srs_engine.core.config import Settings
from srs_engine.core.logging import get_logger

logger = get_logger("srs_engine.core.services.email")


# ---------------------------------------------------------------------------
# Shared SMTP sender
# ---------------------------------------------------------------------------

def _send_smtp(settings: Settings, msg: EmailMessage) -> None:
    if not (settings.smtp_host and settings.smtp_from_email
            and settings.smtp_username and settings.smtp_password):
        raise RuntimeError("SMTP settings are not configured")

    host = settings.smtp_host
    port = settings.smtp_port

    if port == 465:
        server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
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


# ---------------------------------------------------------------------------
# Contact form email (unchanged)
# ---------------------------------------------------------------------------

def _build_contact_message(
    *,
    from_email: str,
    to_email: str,
    name: str,
    email: str,
    subject: str,
    message: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"]     = from_email
    msg["To"]       = to_email
    msg["Subject"]  = f"[SRS_Engine Contact] {subject}"
    msg["Reply-To"] = email

    body = (
        f"New contact form submission:\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Subject: {subject}\n\n"
        f"Message:\n{message}\n"
    )
    msg.set_content(body)
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
        from_email=settings.smtp_from_email or settings.smtp_to_email,
        to_email=settings.smtp_to_email,
        name=name,
        email=email,
        subject=subject,
        message=message,
    )
    logger.info("Sending contact email to %s", settings.smtp_to_email)
    await run_in_threadpool(_send_smtp, settings, msg)


# ---------------------------------------------------------------------------
# SRS completion email — attaches the .docx file directly
# ---------------------------------------------------------------------------

def _build_and_send_srs_email(
    *,
    settings: Settings,
    to_email: str,
    user_display_name: str,
    project_name: str,
    document_path: str,
) -> None:
    """
    Synchronous helper: builds the message with attachment and sends it.
    Called inside run_in_threadpool so disk I/O never blocks the event loop.

    Raises:
        FileNotFoundError: if document_path does not exist on disk.
        ValueError:        if the file is empty.
    """
    doc = Path(document_path)

    if not doc.exists():
        raise FileNotFoundError(
            f"SRS document not found at '{document_path}' — cannot attach."
        )

    file_bytes = doc.read_bytes()

    if len(file_bytes) == 0:
        raise ValueError(
            f"SRS document at '{document_path}' is empty — refusing to attach."
        )

    msg = EmailMessage()
    msg["From"]    = settings.smtp_from_email or settings.smtp_to_email
    msg["To"]      = to_email
    msg["Subject"] = f"[SRS Engine] Your SRS document is ready — {project_name}"

    body = (
        f"Hi {user_display_name},\n\n"
        f"Your Software Requirements Specification document for "
        f"'{project_name}' has been successfully generated.\n\n"
        f"The document is attached to this email as a Word file (.docx).\n"
        f"You can open it in Microsoft Word, Google Docs, or LibreOffice.\n\n"
        f"You can also access it any time from your dashboard at /jobs.\n\n"
        f"— SRS Engine\n"
    )
    msg.set_content(body)

    # Attach the .docx
    msg.add_attachment(
        file_bytes,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=doc.name,      # e.g. "MyProject_SRS.docx"
    )

    _send_smtp(settings, msg)


async def send_srs_complete_email(
    *,
    settings: Settings,
    to_email: str,
    user_display_name: str,
    project_name: str,
    document_path: str,         # ← was download_url, now a file path
) -> None:
    """
    Send the generated SRS document as a .docx email attachment.

    Called by the worker after mark_completed() succeeds.

    Args:
        settings:          App settings (SMTP config).
        to_email:          Recipient email address.
        user_display_name: Used in the greeting line.
        project_name:      Name of the generated project.
        document_path:     Path to the .docx file on disk
                           (e.g. "./srs_engine/generated_srs/uid/Project_SRS.docx").
    """
    if not to_email:
        logger.warning(
            "send_srs_complete_email | Skipped — no email address | project=%s",
            project_name,
        )
        return

    logger.info(
        "send_srs_complete_email | Sending attachment | to=%s | file=%s",
        to_email, document_path,
    )

    await run_in_threadpool(
        _build_and_send_srs_email,
        settings=settings,
        to_email=to_email,
        user_display_name=user_display_name,
        project_name=project_name,
        document_path=document_path,
    )

    logger.info(
        "send_srs_complete_email | Done | to=%s | project=%s",
        to_email, project_name,
    )