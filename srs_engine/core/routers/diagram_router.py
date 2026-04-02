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
GET    /api/diagrams/project/{project_name}/parsed-docs → list parsed docs for Context Selector
"""

import json
from pathlib import Path

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

PARSED_DOCS_ROOT = Path("./parsed_docs")


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


def _build_context_from_docs(user_id: str, document_ids: list[str]) -> str:
    """
    Context Selector helper.
    Reads each parsed_docs/{user_id}/{doc_id}.json and builds a structured
    Page-Index context string to inject into the LLM diagram prompt.
    Only sections that have real content are included, keeping the prompt lean.
    """
    if not document_ids:
        return ""

    blocks: list[str] = []
    for doc_id in document_ids:
        path = PARSED_DOCS_ROOT / user_id / f"{doc_id}.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        meta = data.get("metadata", {})
        filename = meta.get("original_filename", doc_id)
        sections = data.get("sections", [])

        if not sections:
            # Fallback: use raw_text snippet
            raw = data.get("raw_text", "")[:1500]
            if raw:
                blocks.append(f"--- Document: {filename} ---\n{raw}\n")
            continue

        # Build a human-readable Page Index from section headings + content
        def _flatten(secs: list, depth: int = 0) -> list[str]:
            lines = []
            indent = "  " * depth
            for s in secs:
                heading_line = f"{indent}{s.get('section_id', '')} {s.get('heading', '')}"
                content = (s.get("content") or "").strip()
                if content:
                    heading_line += f"\n{indent}  {content[:400]}"
                lines.append(heading_line)
                lines.extend(_flatten(s.get("subsections", []), depth + 1))
            return lines

        page_index_lines = _flatten(sections)
        doc_block = f"--- Document: {filename} ---\n" + "\n".join(page_index_lines)
        blocks.append(doc_block)

    if not blocks:
        return ""

    return "\n\n=== Selected Document Context (Page Index) ===\n" + "\n\n".join(blocks) + "\n=== End Context ===\n"


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


@router.get("/api/diagrams/project/{project_name}/parsed-docs")
async def api_project_parsed_docs(
    project_name: str,
    db=Depends(get_db),
    user=Depends(require_user),
):
    """
    Context Selector: list all parsed documents for a project so the frontend
    can show a multi-select checklist. Returns [{doc_id, filename, section_count}].
    """
    user_id = str(user.get("_id"))
    user_dir = PARSED_DOCS_ROOT / user_id
    if not user_dir.exists():
        return []

    result = []
    for json_path in user_dir.glob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            meta = data.get("metadata", {})
            # Match by project_name stored in metadata if available, else include all
            if "project_name" in meta and meta["project_name"] != project_name:
                continue
            result.append({
                "doc_id": json_path.stem,
                "filename": meta.get("original_filename", json_path.stem),
                "section_count": len(data.get("sections", [])),
                "word_count": meta.get("word_count", 0),
            })
        except Exception:
            continue
    return result


@router.post("/api/diagrams/generate")
async def api_generate_diagram(
    body: DiagramGenerateRequest,
    db=Depends(get_db),
    user=Depends(require_user),
):
    """
    Generate a brand-new diagram from a natural-language prompt.
    If selected_document_ids is provided (Context Selector), those parsed docs
    are used as structured Page Index context.
    Falls back to scanning the project's historical SRS job payloads otherwise.
    """
    user_id = str(user.get("_id"))

    if body.selected_document_ids:
        # ── Context Selector path: use explicitly chosen parsed documents ──────
        context_str = _build_context_from_docs(user_id, body.selected_document_ids)
    else:
        # ── Legacy path: scrape SRS job payloads for the project ──────────────
        from srs_engine.core.db.job_repo import JobRepo
        repo = JobRepo(db)
        jobs = await repo.get_jobs_by_user(user_id, limit=50)
        context_str = ""
        for job in jobs:
            if job.get("project_name") == body.project_name:
                payload = job.get("payload", {})
                prob = payload.get("project_identity", {}).get("problem_statement", "")
                feats = payload.get("functional_scope", {}).get("core_features", [])
                context_str += "\n\n--- Project Context from SRS ---\n"
                if prob:
                    context_str += f"Problem Statement:\n{prob}\n\n"
                if feats:
                    context_str += "Project Structure / Features:\n"
                    for i, f in enumerate(feats, 1):
                        context_str += f"{i}. {f}\n"
                break

    # ── Quick Fix: Sanitizer for ->>> syntax errors in sequence diagrams ──
    if body.diagram_type == "sequence":
        import re
        body.prompt = re.sub(r'->>>', '->>', body.prompt)
        if body.error_feedback:
            body.error_feedback += "\nIMPORTANT: Do not use ->>>. Mermaid sequence diagrams only use ->> (solid) or -->> (dotted)."

    diagram = await create_diagram(
        db=db,
        user_id=user_id,
        project_name=body.project_name,
        prompt=body.prompt,
        diagram_type=body.diagram_type,
        context_str=context_str,
        error_feedback=body.error_feedback,
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

    # ── Build context from selected documents (same as generate) ──────────────
    if body.selected_document_ids:
        context_str = _build_context_from_docs(user_id, body.selected_document_ids)
    else:
        context_str = ""  # No legacy scrape on regenerate — user chose to skip context

    diagram = await regenerate_diagram(
        db=db,
        user_id=user_id,
        diagram_id=diagram_id,
        prompt=body.prompt,
        diagram_type=body.diagram_type,
        context_str=context_str,
        error_feedback=body.error_feedback,
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
