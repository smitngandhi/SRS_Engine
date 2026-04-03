from __future__ import annotations

"""
core/routers/diagram_router.py
────────────────────────────────
Routes for the Diagram Studio feature.

v3 changes vs v2:
  · Auto-load project context from *_sections.json (page-index) when
    selected_document_ids is empty — this was the main context bug.
  · Added detail_level to generate and regenerate request handling.
  · Context priority: selected_document_ids > sections.json (page index) >
    RAG search on query > job-history scrape.
  · Sequence ->>> sanitization moved to diagram_service._sanitize_mermaid.
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

PARSED_DOCS_ROOT   = Path("./parsed_docs")
GENERATED_SRS_ROOT = Path("./srs_engine/generated_srs")

# Human-readable section labels (mirrors chat_router._SECTION_LABELS)
_SECTION_LABELS: dict[str, str] = {
    "introduction_section":        "Introduction",
    "overall_description_section": "Overall Description",
    "system_features_section":     "System Features",
    "external_interfaces_section": "External Interfaces",
    "nfr_section":                 "Non-Functional Requirements",
    "glossary_section":            "Glossary",
    "assumptions_section":         "Assumptions & Dependencies",
}

_SKIP_KEYS = frozenset({"section_id", "section_number", "domain", "project_name"})


# ── Context builders ──────────────────────────────────────────────────────────

def _to_text_brief(obj, max_chars: int = 600) -> str:
    """Compact text representation of a section value (for diagram context)."""
    if isinstance(obj, str):
        return obj.strip()[:max_chars]
    if isinstance(obj, (int, float, bool)):
        return str(obj)
    if isinstance(obj, list):
        parts = []
        for i, item in enumerate(obj[:12], 1):
            if isinstance(item, dict):
                name = (
                    item.get("name") or item.get("title") or
                    item.get("feature_name") or item.get("term") or f"Item {i}"
                )
                parts.append(f"  {i}. {str(name)[:80]}")
            else:
                parts.append(f"  {i}. {str(item)[:80]}")
        return "\n".join(parts)
    if isinstance(obj, dict):
        parts = []
        for k, v in obj.items():
            if k in _SKIP_KEYS:
                continue
            label = k.replace("_", " ").title()
            val_str = _to_text_brief(v, max_chars=200)
            if val_str:
                parts.append(f"  {label}: {val_str}")
        return "\n".join(parts)
    return repr(obj)[:max_chars]


def _build_context_from_sections_json(user_id: str, project_name: str) -> str:
    """
    PRIMARY context source: load {project_name}_sections.json and build a
    compact Page-Index context string using PAGE_INDEX_MAP ordering.

    This gives the LLM structured knowledge about the project's features,
    architecture, interfaces, and requirements — all from the generated SRS.
    """
    path = GENERATED_SRS_ROOT / user_id / f"{project_name}_sections.json"
    if not path.exists():
        return ""

    try:
        sections_json: dict = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""

    domain = sections_json.get("domain", "technical")

    try:
        from srs_engine.utils.page_index_map import get_all_sections
        entries = get_all_sections(domain)
    except Exception:
        entries = [
            {"page_index": i * 10, "section_key": k}
            for i, k in enumerate(_SECTION_LABELS, 1)
        ]

    blocks: list[str] = []
    for entry in entries:
        key  = entry["section_key"]
        data = sections_json.get(key)
        if not data:
            continue
        label = _SECTION_LABELS.get(key, key.replace("_", " ").title())
        content = _to_text_brief(data, max_chars=800)
        if content.strip():
            blocks.append(f"[{label}]\n{content}")

    if not blocks:
        return ""

    return (
        "\n\n=== Project SRS Context (Page Index) ===\n"
        + "\n\n".join(blocks)
        + "\n=== End SRS Context ===\n"
    )


def _build_context_from_rag(
    user_id: str, project_name: str, query: str
) -> str:
    """
    FALLBACK: use FAISS RAG to find the most relevant section for this query.
    Returns empty string if RAG index doesn't exist or confidence is too low.
    """
    try:
        from srs_engine.utils.srs_rag_index import search_section
        section_key, confidence = search_section(
            query=query,
            user_id=user_id,
            project_name=project_name,
            top_k=1,
        )
        if not section_key or confidence < 0.30:
            return ""

        path = GENERATED_SRS_ROOT / user_id / f"{project_name}_sections.json"
        if not path.exists():
            return ""
        sections_json = json.loads(path.read_text(encoding="utf-8"))
        data = sections_json.get(section_key)
        if not data:
            return ""

        label = _SECTION_LABELS.get(section_key, section_key.replace("_", " ").title())
        content = _to_text_brief(data, max_chars=1200)
        return (
            f"\n\n=== Most Relevant SRS Section (RAG, confidence={confidence:.0%}) ===\n"
            f"[{label}]\n{content}\n=== End RAG Context ===\n"
        )
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def _build_context_from_parsed_docs(user_id: str, document_ids: list[str]) -> str:
    """Build context from explicitly selected parsed document IDs."""
    if not document_ids:
        return ""

    blocks: list[str] = []
    for doc_id in document_ids:
        p = PARSED_DOCS_ROOT / user_id / f"{doc_id}.json"
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        meta     = data.get("metadata", {})
        filename = meta.get("original_filename", doc_id)
        sections = data.get("sections", [])

        if not sections:
            raw = data.get("raw_text", "")[:1500]
            if raw:
                blocks.append(f"--- Document: {filename} ---\n{raw}\n")
            continue

        def _flatten(secs: list, depth: int = 0) -> list[str]:
            lines = []
            indent = "  " * depth
            for s in secs:
                heading = f"{indent}{s.get('section_id', '')} {s.get('heading', '')}"
                content = (s.get("content") or "").strip()
                if content:
                    heading += f"\n{indent}  {content[:400]}"
                lines.append(heading)
                lines.extend(_flatten(s.get("subsections", []), depth + 1))
            return lines

        doc_block = f"--- Document: {filename} ---\n" + "\n".join(_flatten(sections))
        blocks.append(doc_block)

    if not blocks:
        return ""
    return "\n\n=== Selected Document Context ===\n" + "\n\n".join(blocks) + "\n=== End Context ===\n"


def _get_context(
    user_id: str,
    project_name: str,
    prompt: str,
    selected_document_ids: list[str],
) -> str:
    """
    Resolve context in priority order:
      1. Explicitly selected parsed docs  (Context Selector)
      2. Project _sections.json           (auto-loaded page index from generated SRS)
      3. RAG search on the prompt         (FAISS fallback for targeted retrieval)
      4. Job-history scrape               (last resort — no SRS generated yet)
    """
    # 1. Explicit doc selection
    if selected_document_ids:
        ctx = _build_context_from_parsed_docs(user_id, selected_document_ids)
        if ctx:
            return ctx

    # 2. Auto-load from generated SRS sections.json  ← THE KEY BUG FIX
    ctx = _build_context_from_sections_json(user_id, project_name)
    if ctx:
        return ctx

    # 3. RAG fallback
    ctx = _build_context_from_rag(user_id, project_name, prompt)
    if ctx:
        return ctx

    # 4. Legacy: scrape SRS job payloads
    return ""  # router will handle the job scrape below if needed


# ── Render helper ──────────────────────────────────────────────────────────────

def _render(request: Request, template: str, **ctx):
    return request.app.state.templates.TemplateResponse(
        template,
        {
            "request":      request,
            "is_logged_in": bool(request.session.get("user_id")),
            "user":         request.session.get("display_name"),
            **ctx,
        },
    )


# ── Page route ────────────────────────────────────────────────────────────────

@router.get("/diagrams")
async def diagram_studio_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login?next=/diagrams", status_code=302)
    return _render(request, "pages/diagram_studio.html")


# ── API: recent + projects ─────────────────────────────────────────────────────

@router.get("/api/diagrams/recent")
async def api_recent_diagrams(db=Depends(get_db), user=Depends(require_user)):
    user_id = str(user.get("_id"))
    diagrams = await list_recent_diagrams(db, user_id)
    return [d.dict() for d in diagrams]


@router.get("/api/diagrams/projects")
async def api_diagram_projects(db=Depends(get_db), user=Depends(require_user)):
    user_id = str(user.get("_id"))
    return await list_user_projects(db, user_id)


# ── API: Context Selector (parsed docs) ───────────────────────────────────────

@router.get("/api/diagrams/project/{project_name}/parsed-docs")
async def api_project_parsed_docs(
    project_name: str,
    db=Depends(get_db),
    user=Depends(require_user),
):
    user_id  = str(user.get("_id"))
    user_dir = PARSED_DOCS_ROOT / user_id
    if not user_dir.exists():
        return []

    result = []
    for json_path in user_dir.glob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            meta = data.get("metadata", {})
            if "project_name" in meta and meta["project_name"] != project_name:
                continue
            result.append({
                "doc_id":        json_path.stem,
                "filename":      meta.get("original_filename", json_path.stem),
                "section_count": len(data.get("sections", [])),
                "word_count":    meta.get("word_count", 0),
            })
        except Exception:
            continue
    return result


# ── API: Generate ──────────────────────────────────────────────────────────────

@router.post("/api/diagrams/generate")
async def api_generate_diagram(
    body: DiagramGenerateRequest,
    db=Depends(get_db),
    user=Depends(require_user),
):
    """
    Generate a brand-new diagram.

    Context priority:
      1. selected_document_ids (Context Selector) if provided
      2. Auto-load from {project_name}_sections.json (page index) — KEY FIX
      3. RAG fallback
      4. Job history scrape (legacy, last resort)
    """
    user_id = str(user.get("_id"))

    context_str = _get_context(
        user_id=user_id,
        project_name=body.project_name,
        prompt=body.prompt,
        selected_document_ids=body.selected_document_ids,
    )

    # Last resort: scrape job history
    if not context_str:
        try:
            from srs_engine.core.db.job_repo import JobRepo
            repo = JobRepo(db)
            jobs = await repo.get_jobs_by_user(user_id, limit=50)
            for job in jobs:
                if job.get("project_name") == body.project_name:
                    payload = job.get("payload", {})
                    prob    = payload.get("project_identity", {}).get("problem_statement", "")
                    feats   = payload.get("functional_scope", {}).get("core_features", [])
                    if prob or feats:
                        context_str = "\n\n=== Project Context (from SRS job) ===\n"
                        if prob:
                            context_str += f"Problem Statement:\n{prob}\n\n"
                        if feats:
                            context_str += "Core Features:\n"
                            for i, f in enumerate(feats[:20], 1):
                                context_str += f"  {i}. {f}\n"
                        context_str += "=== End Context ===\n"
                    break
        except Exception:
            pass

    diagram = await create_diagram(
        db=db,
        user_id=user_id,
        project_name=body.project_name,
        prompt=body.prompt,
        diagram_type=body.diagram_type,
        context_str=context_str,
        error_feedback=body.error_feedback,
        detail_level=body.detail_level,
    )
    return diagram.dict()


# ── API: Project diagrams ──────────────────────────────────────────────────────

@router.get("/api/diagrams/project/{project_name}")
async def api_project_diagrams(
    project_name: str,
    db=Depends(get_db),
    user=Depends(require_user),
):
    user_id  = str(user.get("_id"))
    diagrams = await list_diagrams_by_project(db, user_id, project_name)
    return [d.dict() for d in diagrams]


# ── API: Get single diagram ────────────────────────────────────────────────────

@router.get("/api/diagrams/{diagram_id}")
async def api_get_diagram(
    diagram_id: str,
    db=Depends(get_db),
    user=Depends(require_user),
):
    user_id = str(user.get("_id"))
    diagram = await get_diagram(db, user_id, diagram_id)
    return diagram.dict()


# ── API: Regenerate ────────────────────────────────────────────────────────────

@router.post("/api/diagrams/{diagram_id}/regenerate")
async def api_regenerate_diagram(
    diagram_id: str,
    body: DiagramRegenerateRequest,
    db=Depends(get_db),
    user=Depends(require_user),
):
    user_id = str(user.get("_id"))

    # Resolve project_name from the existing diagram for context loading
    existing = await get_diagram(db, user_id, diagram_id)
    project_name = existing.project_name if existing else ""

    context_str = _get_context(
        user_id=user_id,
        project_name=project_name,
        prompt=body.prompt,
        selected_document_ids=body.selected_document_ids,
    )

    diagram = await regenerate_diagram(
        db=db,
        user_id=user_id,
        diagram_id=diagram_id,
        prompt=body.prompt,
        diagram_type=body.diagram_type,
        context_str=context_str,
        error_feedback=body.error_feedback,
        detail_level=body.detail_level,
    )
    return diagram.dict()


# ── API: Edit ──────────────────────────────────────────────────────────────────

@router.patch("/api/diagrams/{diagram_id}/edit")
async def api_edit_diagram(
    diagram_id: str,
    body: DiagramEditRequest,
    db=Depends(get_db),
    user=Depends(require_user),
):
    user_id = str(user.get("_id"))
    diagram = await save_edited_diagram(db, user_id, diagram_id, body.mermaid_code)
    return diagram.dict()


# ── API: Delete ────────────────────────────────────────────────────────────────

@router.delete("/api/diagrams/{diagram_id}")
async def api_delete_diagram(
    diagram_id: str,
    db=Depends(get_db),
    user=Depends(require_user),
):
    user_id = str(user.get("_id"))
    deleted = await delete_diagram(db, user_id, diagram_id)
    return {"success": deleted}