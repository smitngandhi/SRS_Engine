from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates  # type: ignore[attr-defined]


def _is_logged_in(request: Request) -> bool:
    return bool(request.session.get("user_id"))  # type: ignore[attr-defined]


def _render(request: Request, template: str, **ctx):
    """Shorthand to render a template with common context."""
    return _templates(request).TemplateResponse(
        template, {"request": request, "is_logged_in": _is_logged_in(request), **ctx}
    )


# ── Auth redirects ────────────────────────────────────────────────────────────

@router.get("/")
async def root(request: Request):
    """Always redirect root to /home. Login is only required for protected actions."""
    return RedirectResponse(url="/home", status_code=302)


@router.get("/login")
async def login_page(request: Request):
    """Show login page. Redirect to /home if already logged in."""
    if _is_logged_in(request):
        return RedirectResponse(url="/home", status_code=302)
    error = request.query_params.get("error")
    return _templates(request).TemplateResponse(
        "login.html", {"request": request, "error": error}
    )


# ── Public pages (no login required) ─────────────────────────────────────────

@router.get("/home")
async def home(request: Request):
    """Main landing page — single scrollable page (hero, features, faqs, about, contact)."""
    print("Rendering Home page")
    return _render(request, "pages/landing.html")


@router.get("/srs-generator")
async def srs_generator(request: Request):
    """SRS generator form — where users fill in project details to generate a .docx."""
    print("Rendering SRS Generator page")
    return _render(request, "pages/srs_generator.html")