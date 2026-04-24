from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, File, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import random
from srs_engine.core.auth.deps import require_user
from srs_engine.core.db.mongo import get_db
from srs_engine.core.db.file_storage import FileStorage
from urllib.parse import unquote

router = APIRouter()

QUOTES = [
    "First, solve the problem. Then, write the code. — John Johnson",
    "Code is like humor. When you have to explain it, it's bad. — Cory House",
    "Fix the cause, not the symptom. — Steve Maguire",
    "Simplicity is the soul of efficiency. — Austin Freeman",
    "Make it work, make it right, make it fast. — Kent Beck",
    "Every great developer you know got there by solving problems they were unqualified to solve until they actually did it. — Patrick McKenzie",
    "Talk is cheap. Show me the code. — Linus Torvalds",
    "The best way to predict the future is to invent it. — Alan Kay",
    "Software is a great combination between artistry and engineering. — Bill Gates",
    "Innovation distinguishes between a leader and a follower. — Steve Jobs",
    "The best requirements are those that disappear through elegant design. — SpecForge AI",
    "Documentation is a love letter that you write to your future self. — Damian Conway",
    "Requirements are not what the user says, but what the user needs. — Unknown",
    "Design is not just what it looks like and feels like. Design is how it works. — Steve Jobs",
    "A good SRS is the compass that keeps the project on course. — SpecForge AI",
    "The most expensive part of software is the part that was never written. — Unknown",
    "Measuring programming progress by lines of code is like measuring aircraft building progress by weight. — Bill Gates",
    "The function of good software is to make the complex appear to be simple. — Grady Booch",
    "Quality is not an act, it is a habit. — Aristotle",
    "Software architecture is the art of drawing lines that you don't cross. — Robert C. Martin",
    "Requirements engineering is the most difficult part of software development. — Fred Brooks",
    "An SRS should be clear enough for a human and precise enough for an agent. — SpecForge AI",
    "Agility is the ability to adapt to change, not the absence of a plan. — Unknown",
    "The best error message is the one that never shows up. — Thomas Fuchs",
    "Software is the only limit to our imagination. — Unknown",
    "Code never lies, comments sometimes do. — Ron Jeffries",
    "Optimization is the root of all evil. — Donald Knuth",
    "Great software is built on a foundation of solid requirements. — SpecForge AI",
    "The sooner you start to code, the longer the program will take. — Roy Carlson",
    "A user interface is like a joke. If you have to explain it, it's not that good. — Unknown",
    "System analysis is the process of understanding what is requested. — Unknown",
    "Architectural decisions are those that are hard to change later. — Martin Fowler",
    "AI doesn't replace the architect; it gives the architect a faster brush. — SpecForge AI",
    "Refactoring is the process of changing a software system in such a way that it does not alter the external behavior. — Martin Fowler",
    "Complexity is the enemy of reliability. — Unknown",
    "Good design is obvious. Great design is transparent. — Joe Sparano",
    "Requirements should be verifiable, not just aspirational. — SpecForge AI",
    "Don't comment bad code—rewrite it. — Brian Kernighan",
    "The best tool for requirements is a clear mind. — Unknown",
    "Automation is not about doing things faster, but doing things right every time. — SpecForge AI",
    "Technical debt is a loan that you never stop paying interest on. — Ward Cunningham",
    "The user's experience is the ultimate metric of success. — Unknown",
    "Software is eating the world, and requirements are the menu. — SpecForge AI",
    "A requirement is a bridge between a problem and a solution. — Unknown",
    "Iteration is the key to perfection. — Unknown",
    "Consistency is the hallmark of professional software. — SpecForge AI",
    "The most important requirement is the one the customer forgot to mention. — Unknown",
    "Build for the user, but design for the system. — SpecForge AI",
    "Clear requirements save more time than fast typing. — Unknown",
    "SpecForge AI: Forging the future of requirements, one section at a time."
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates  # type: ignore[attr-defined]


def _is_logged_in(request: Request) -> bool:
    return bool(request.session.get("user_id"))  # type: ignore[attr-defined]


def _render(request: Request, template: str, **ctx):
    """Shorthand to render a template with common context."""
    user_id = request.session.get("user_id")
    avatar_url = None
    if user_id and request.session.get("has_avatar"): # Optimization: check a session flag
         avatar_url = f"/api/user/avatar/{user_id}"
    
    # Alternatively, just always check if we don't want session flags
    # avatar_url = f"/api/user/avatar/{user_id}" if user_id else None

    return _templates(request).TemplateResponse(
        template, {
            "request": request,
            "is_logged_in": _is_logged_in(request),
            "user": request.session.get("display_name"),
            "avatar_url": avatar_url,
            **ctx
        }
    )


# ── Auth redirects ────────────────────────────────────────────────────────────

@router.get("/")
async def root(request: Request):
    """Always redirect root to /home. Login is only required for protected actions."""
    return RedirectResponse(url="/home", status_code=302)


@router.get("/health")
async def health_check():
    """Simple health check endpoint for monitoring/deployment."""
    return {"status": "ok", "service": "SpecForge AI Backend"}


@router.get("/login")
async def login_page(request: Request):
    """Show login page. Redirect to /home if already logged in."""
    if _is_logged_in(request):
        return RedirectResponse(url="/home", status_code=302)
    error = request.query_params.get("error")
    return _templates(request).TemplateResponse(
        "login.html", {"request": request, "error": error}
    )


@router.get("/verify")
async def verify_page(request: Request, db=Depends(get_db)):
    """Show the OTP verification page."""
    from srs_engine.core.db.user_repo import UserRepo
    from datetime import datetime, timezone

    user_id = request.session.get("verify_user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    
    repo = UserRepo(db)
    user = await repo.get_by_id(user_id)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    expires_at = user.get("otp_expires_at")
    expires_in = 0
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        remaining = (expires_at - datetime.now(timezone.utc)).total_seconds()
        expires_in = max(0, int(remaining))

    error = request.query_params.get("error")
    return _render(
        request, 
        "verify.html", 
        error=error,
        expires_in=expires_in
    )


# ── Public pages (no login required) ─────────────────────────────────────────

@router.get("/home")
async def home(request: Request):
    """Main landing page — single scrollable page (hero, features, faqs, about, contact)."""
    return _render(request, "pages/landing.html")


@router.get("/srs-generator")
async def srs_generator(request: Request):
    """SRS generator form — where users fill in project details to generate a .docx."""
    if not _is_logged_in(request):
        return RedirectResponse(url="/login?next=/srs-generator", status_code=302)
    return _render(request, "pages/srs_generator.html")


# ── GET /api/my-documents ─────────────────────────────────────
@router.get("/api/my-documents")
async def get_my_documents(user=Depends(require_user), db=Depends(get_db)):
    """Return list of all SRS documents generated by the logged-in user from GridFS."""
    user_id = str(user.get("_id"))
    fs = FileStorage(db)
    
    # List all docx files for this user
    files = await fs.list_files({"type": "docx", "user_id": user_id})
    
    documents = []
    for f in sorted(files, key=lambda x: x["upload_date"], reverse=True):
        project_name = f["metadata"].get("project_name", "Unknown")
        documents.append({
            "id": f"{project_name}_SRS",
            "project_name": project_name,
            "domain": f["metadata"].get("domain", "General"),
            "filename": f["filename"],
            "created_at": f["upload_date"].timestamp(),
            "size_kb": round(f["length"] / 1024, 1),
        })

    return documents


# ── GET /api/download-srs/{doc_id} ────────────────────────────
@router.get("/api/download-srs/{doc_id}")
async def download_srs(doc_id: str, user=Depends(require_user), db=Depends(get_db)):
    """Download a specific SRS .docx from GridFS — scoped to the logged-in user."""
    user_id = str(user.get("_id"))

    if "/" in doc_id or "\\" in doc_id or ".." in doc_id:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    # BUG FIX: handle URL encoding (e.g. %20 for spaces)
    project_name = unquote(doc_id).removesuffix("_SRS")
    fs = FileStorage(db)
    data = await fs.get_file({"type": "docx", "user_id": user_id, "project_name": project_name})

    if not data:
        raise HTTPException(status_code=404, detail="Document not found")

    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{project_name}_SRS.docx"'}
    )


# ── SRS Upgrader pages ────────────────────────────────────────

@router.get("/srs-upgrader")
async def srs_upgrader(request: Request):
    """Step 1: Upload page."""
    if not _is_logged_in(request):
        return RedirectResponse(url="/login?next=/srs-upgrader", status_code=302)
    return _render(request, "pages/srs_upgrader.html")


# ── Generated SRS Upgrader pages ──────────────────────────────

@router.get("/srs-generated-upgrader")
async def srs_generated_upgrader(request: Request):
    """Pick a generated SRS document to upgrade."""
    if not _is_logged_in(request):
        return RedirectResponse(url="/login?next=/srs-generated-upgrader", status_code=302)
    return _render(request, "pages/srs_generated_upgrader.html")


@router.get("/srs-section-upgrader")
async def srs_section_upgrader(request: Request):
    """Upgrade individual sections of a generated SRS document."""
    if not _is_logged_in(request):
        return RedirectResponse(url="/login?next=/srs-section-upgrader", status_code=302)
    return _render(request, "pages/srs_section_upgrader.html")


@router.get("/srs-history")
async def srs_history(request: Request):
    """View version history and restore old versions of a project."""
    if not _is_logged_in(request):
        return RedirectResponse(url="/login?next=/srs-history", status_code=302)
    return _render(request, "pages/srs_history.html")


@router.get("/srs-upgrader/review/{file_id}")
async def srs_upgrader_review(file_id: str, request: Request):
    """Step 2: Analysis, Q&A, and diff review for a parsed SRS file."""
    from srs_engine.core.services.upload_service import list_uploads

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url=f"/login?next=/srs-upgrader/review/{file_id}", status_code=302)

    # Security: block path traversal
    if "/" in file_id or "\\" in file_id or ".." in file_id:
        raise HTTPException(status_code=400, detail="Invalid file ID")

    # Resolve original filename for display in the template
    uploads = await list_uploads(user_id)
    record = next((u for u in uploads if u["file_id"] == file_id), None)

    if not record:
        raise HTTPException(
            status_code=404,
            detail="File not found. Upload and parse it first.",
        )

    return _render(
        request,
        "pages/upgrader_review.html",
        file_id=file_id,
        filename=record["original_filename"],
    )

@router.get("/jobs")
async def jobs_page(request: Request):
    """
    Render the job tracker page.
    If user is not logged in, redirect to login page (HTML redirect, not JSON).
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login?next=/jobs", status_code=302)

    return request.app.state.templates.TemplateResponse(
        "pages/job_tracker.html",
        {
            "request":      request,
            "is_logged_in": True,
        },
    )

@router.get("/project-buckets")
async def project_buckets_page(request: Request):
    """
    Render the Project Buckets page.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login?next=/project-buckets", status_code=302)
    
    return _render(request, "pages/project_buckets.html")

@router.get("/document-navigator")
async def document_navigator_page(request: Request):
    """
    Render the new Agentic Document Navigator page.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login?next=/document-navigator", status_code=302)
    
    return _render(request, "pages/document_navigator.html")

@router.get("/profile")
async def profile_page(request: Request, user=Depends(require_user)):
    """Render the user profile page with a random quote."""
    quote = random.choice(QUOTES)
    avatar_url = f"/api/user/avatar/{user['_id']}" if user.get("avatar_file_id") else None
    
    return _render(
        request, 
        "pages/profile.html", 
        quote=quote,
        full_user=user,
        avatar_url=avatar_url
    )


@router.get("/api/user/avatar/{user_id}")
async def get_avatar(user_id: str, db=Depends(get_db)):
    """Serve the user's avatar from GridFS."""
    from srs_engine.core.db.user_repo import UserRepo
    repo = UserRepo(db)
    user = await repo.get_by_id(user_id)
    
    if not user or not user.get("avatar_file_id"):
        raise HTTPException(status_code=404, detail="Avatar not found")
    
    fs = FileStorage(db)
    data = await fs.get_file_by_id(str(user["avatar_file_id"]))
    
    if not data:
        raise HTTPException(status_code=404, detail="Avatar data not found")
        
    return Response(content=data, media_type="image/png")


@router.post("/api/user/avatar/upload")
async def upload_avatar(
    request: Request, 
    avatar: UploadFile = File(...), 
    user=Depends(require_user), 
    db=Depends(get_db)
):
    """Upload and save user avatar to GridFS."""
    content = await avatar.read()
    if len(content) > 1 * 1024 * 1024: # 1MB limit
        raise HTTPException(status_code=400, detail="File too large (max 1MB)")
    
    fs = FileStorage(db)
    # save_file(data, filename, metadata)
    file_id = await fs.save_file(
        content,
        f"avatar_{user['_id']}.png",
        {"type": "avatar", "user_id": str(user["_id"])}
    )
    
    # Update user doc
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"avatar_file_id": file_id}}
    )
    
    # Update session flag immediately
    request.session["has_avatar"] = True
    
    return {"status": "ok", "avatar_url": f"/api/user/avatar/{user['_id']}"}
