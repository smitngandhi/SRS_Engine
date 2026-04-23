from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request

from srs_engine.core.auth.deps import require_user
from srs_engine.core.config import get_settings
from srs_engine.core.services.email_service import send_contact_email


router = APIRouter()


class ContactPayload(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    subject: str = Field(min_length=2, max_length=160)
    message: str = Field(min_length=10, max_length=5000)

    # Honeypot
    website: str | None = None


@router.post("/api/contact")
async def submit_contact(payload: ContactPayload, request: Request):
    # Honeypot (basic spam mitigation)
    if payload.website:
        return {"ok": True}

    if "@" not in payload.email or "." not in payload.email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    settings = get_settings()
    try:
        await send_contact_email(
            settings=settings,
            name=payload.name,
            email=str(payload.email),
            subject=payload.subject,
            message=payload.message,
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

