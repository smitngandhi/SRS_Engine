from __future__ import annotations

"""
diagram_router.py
─────────────────
Routes for the Diagram Studio feature.

GET    /diagrams                               → diagram studio page
GET    /api/diagrams/recent                    → last 6 diagrams (home widget)
GET    /api/diagrams/projects                  → list project names with diagrams
POST   /api/diagrams/generate                  → create new diagram (LLM → SVG)
GET    /api/diagrams/{diagram_id}              → load diagram + all versions
POST   /api/diagrams/{diagram_id}/regenerate   → add new LLM version
PATCH  /api/diagrams/{diagram_id}/edit         → save manually edited mermaid code
DELETE /api/diagrams/{diagram_id}              → delete diagram
GET    /api/diagrams/project/{project_name}    → all diagrams for a project
GET    /api/diagrams/svg/{user_id}/{diagram_id}/v{version}.svg → serve SVG
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse

from srs_engine.core.auth.deps import require_user
from srs_engine.core.db.mongo import get_db
from srs_engine.core.services.diagram_service import (
    create_diagram,
    delete_diagram,
    get_diagram,
    list_diagrams_by_project,
    list_recent_diagrams,
    list_user_projects,
    regenerate_diagram,
    save_edited_diagram,
)
from srs_engine.schemas.diagram_schemas.diagram_schemas import (
    DiagramEditRequest,
    DiagramGenerateRequest,
    DiagramRegenerateRequest,
)

router = APIRouter()


def _render(request: Request, template: str, **ctx):
    return request.app.state.templates.TemplateResponse(
        template,
        {
            "request": request,
            "is_logged_in": bool(request.session.get("user_id")),
            "user": request.session.get("display_name"),
            **ctx,
        },
    )


# ── Page route ────────────────────────────────────────────────────────────────

@router.get("/diagrams")
async def diagram_studio_page(request: Request):
    """Render the Diagram Studio page."""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login?next=/diagrams", status_code=302)
    return _render(request, "pages/diagram_studio.html")


# ── API routes ────────────────────────────────────────────────────────────────

@router.get("/api/diagrams/recent")
async def api_recent_diagrams(db=Depends(get_db), user=Depends(require_user)):
    """Return the 6 most-recently updated diagrams for the home page widget."""
    user_id = str(user.get("_id"))
    diagrams = await list_recent_diagrams(db, user_id)
    return [d.dict() for d in diagrams]


@router.get("/api/diagrams/projects")
async def api_diagram_projects(db=Depends(get_db), user=Depends(require_user)):
    """Return unique project names that have at least one diagram."""
    user_id = str(user.get("_id"))
    return await list_user_projects(db, user_id)


@router.post("/api/diagrams/generate")
async def api_generate_diagram(
    body: DiagramGenerateRequest,
    db=Depends(get_db),
    user=Depends(require_user),
):
    """Generate a brand-new diagram from a natural-language prompt."""
    user_id = str(user.get("_id"))
    
    from srs_engine.core.db.job_repo import JobRepo
    repo = JobRepo(db)
    jobs = await repo.get_jobs_by_user(user_id, limit=50)
    
    context_str = ""
    for job in jobs:
        if job.get("project_name") == body.project_name:
            payload = job.get("payload", {})
            prob = payload.get("problem_statement", "")
            feats = payload.get("features", [])
            
            context_str += "\n\n--- Project Context from SRS ---\n"
            if prob:
                context_str += f"Problem Statement:\n{prob}\n\n"
            if feats:
                context_str += "Project Structure / Features:\n"
                for i, f in enumerate(feats, 1):
                    title = f.get("title", "")
                    desc = f.get("description", "")
                    context_str += f"{i}. {title}: {desc}\n"
            break
            
    enhanced_prompt = body.prompt + context_str

    diagram = await create_diagram(
        db=db,
        user_id=user_id,
        project_name=body.project_name,
        prompt=enhanced_prompt,
        diagram_type=body.diagram_type,
    )
    return diagram.dict()


@router.get("/api/diagrams/project/{project_name}")
async def api_project_diagrams(
    project_name: str,
    db=Depends(get_db),
    user=Depends(require_user),
):
    """Return all diagrams for a specific project."""
    user_id = str(user.get("_id"))
    diagrams = await list_diagrams_by_project(db, user_id, project_name)
    return [d.dict() for d in diagrams]


@router.get("/api/diagrams/{diagram_id}")
async def api_get_diagram(
    diagram_id: str,
    db=Depends(get_db),
    user=Depends(require_user),
):
    """Load a single diagram with all its versions."""
    user_id = str(user.get("_id"))
    diagram = await get_diagram(db, user_id, diagram_id)
    return diagram.dict()


@router.post("/api/diagrams/{diagram_id}/regenerate")
async def api_regenerate_diagram(
    diagram_id: str,
    body: DiagramRegenerateRequest,
    db=Depends(get_db),
    user=Depends(require_user),
):
    """Add a new version generated from a revised prompt."""
    user_id = str(user.get("_id"))
    diagram = await regenerate_diagram(
        db=db,
        user_id=user_id,
        diagram_id=diagram_id,
        prompt=body.prompt,
        diagram_type=body.diagram_type,
    )
    return diagram.dict()


@router.patch("/api/diagrams/{diagram_id}/edit")
async def api_edit_diagram(
    diagram_id: str,
    body: DiagramEditRequest,
    db=Depends(get_db),
    user=Depends(require_user),
):
    """Save manually edited Mermaid code as a new version."""
    user_id = str(user.get("_id"))
    diagram = await save_edited_diagram(db, user_id, diagram_id, body.mermaid_code)
    return diagram.dict()


@router.delete("/api/diagrams/{diagram_id}")
async def api_delete_diagram(
    diagram_id: str,
    db=Depends(get_db),
    user=Depends(require_user),
):
    """Delete a diagram and its SVG files."""
    user_id = str(user.get("_id"))
    deleted = await delete_diagram(db, user_id, diagram_id)
    return {"success": deleted}
