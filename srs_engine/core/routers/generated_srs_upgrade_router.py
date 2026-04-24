"""
core/routers/generated_srs_upgrade_router.py
────────────────────────────────────────────
API routes for upgrading SRS documents generated on this platform.

Completely separate from the existing upload-based upgrade_router.py.
"""

from __future__ import annotations

from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from srs_engine.core.auth.deps import require_user
from srs_engine.core.services.generated_srs_upgrade_service import (
    confirm_upgrade,
    get_section_by_pageindex,
    get_version_history,
    list_generated_srs,
    preview_upgrade,
    rebuild_docx,
    restore_version,
    search_section_rag,
)
from srs_engine.core.db.quota_repo import QuotaRepo

from srs_engine.core.db.mongo import get_db
from srs_engine.core.db.file_storage import FileStorage
from srs_engine.core.services.generated_srs_upgrade_service import BASE_DIR as GENERATED_DIR


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


router = APIRouter(prefix="/upgrade/generated", tags=["generated-upgrade"])


# ── Shared guard ──────────────────────────────────────────────────────────────

def _validate_project_name(project: str) -> None:
    """
    Reject project names that contain path-traversal sequences.
    """
    if not project or "/" in project or "\\" in project or ".." in project:
        raise HTTPException(status_code=400, detail="Invalid project name")

def _clean_project_name(project: str) -> str:
    """Strip _SRS suffix if present (compatibility with landing page IDs)."""
    if project.endswith("_SRS"):
        return project[:-4]
    return project


# ── Request bodies ────────────────────────────────────────────────────────────

class SearchRequest(StrictBaseModel):
    query: str


class PreviewRequest(StrictBaseModel):
    instruction: str
    lookup_method: str = "pageindex"


class ConfirmRequest(StrictBaseModel):
    upgraded_json: dict


class RebuildRequest(StrictBaseModel):
    comment: str = "No comment"


class RestoreRequest(StrictBaseModel):
    version: int


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/list")
async def list_docs(user=Depends(require_user), db=Depends(get_db)):
    """List all generated SRS documents for the logged-in user."""
    user_id = str(user.get("_id"))
    docs = await list_generated_srs(user_id, db)
    return {"success": True, "documents": docs}


@router.get("/{project}/section/{page_index}")
async def get_section(
    project: str,
    page_index: int,
    user=Depends(require_user),
    db=Depends(get_db),
):
    """
    Fast path: look up a section by page_index.
    """
    project = unquote(project)
    _validate_project_name(project)
    project = _clean_project_name(project)
    user_id = str(user.get("_id"))
    try:
        result = await get_section_by_pageindex(user_id, project, page_index, db)
        return {
            "success": True,
            "page_index": result.page_index,
            "section_key": result.section_key,
            "section_type": result.section_type,
            "section_data": result.section_data,
            "lookup_method": result.lookup_method,
        }
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{project}/search")
async def search_section(
    project: str,
    body: SearchRequest,
    user=Depends(require_user),
    db=Depends(get_db),
):
    """
    RAG fallback: search for the most relevant section using FAISS.
    """
    project = unquote(project)
    _validate_project_name(project)
    project = _clean_project_name(project)
    user_id = str(user.get("_id"))
    try:
        result = await search_section_rag(user_id, project, body.query, db)
        return {
            "success": True,
            "page_index": result.page_index,
            "section_key": result.section_key,
            "section_type": result.section_type,
            "section_data": result.section_data,
            "lookup_method": result.lookup_method,
            "confidence": result.rag_confidence,
        }
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{project}/section/{page_index}/preview")
async def preview(
    project: str,
    page_index: int,
    body: PreviewRequest,
    user=Depends(require_user),
    db=Depends(get_db),
):
    """
    Call the upgrade agent and return a preview (original + upgraded JSON).
    """
    project = unquote(project)
    _validate_project_name(project)
    project = _clean_project_name(project)
    user_id = str(user.get("_id"))

    # ── Quota Check ───────────────────────────────────
    quota = QuotaRepo(db)
    limit = user.get("custom_upgrade_count_limit", 2)
    allowed = await quota.check_quota(user_id, "upgrade_count", project_name=project, limit=limit)
    if not allowed:
        raise HTTPException(
            status_code=429, 
            detail=f"You've reached your plan limit of {limit} upgrades for this project."
        )

    try:
        result = await preview_upgrade(
            user_id=user_id,
            project_name=project,
            page_index=page_index,
            instruction=body.instruction,
            lookup_method=body.lookup_method,
            db=db,
        )
        return {"success": True, **result}
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project}/section/{page_index}/confirm")
async def confirm(
    project: str,
    page_index: int,
    body: ConfirmRequest,
    user=Depends(require_user),
    db=Depends(get_db),
):
    """
    Persist the upgraded section JSON.
    """
    project = unquote(project)
    _validate_project_name(project)
    project = _clean_project_name(project)
    user_id = str(user.get("_id"))
    try:
        await confirm_upgrade(
            user_id=user_id,
            project_name=project,
            page_index=page_index,
            upgraded_json=body.upgraded_json,
            db=db,
        )
        
        # Increment upgrade count after successful confirmation
        quota = QuotaRepo(db)
        await quota.increment_quota(user_id, "upgrade_count", project_name=project)

        return {"success": True, "message": "Section upgraded and saved."}
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project}/rebuild")
async def rebuild(
    project: str,
    body: RebuildRequest,
    user=Depends(require_user),
    db=Depends(get_db),
):
    """
    Rebuild the .docx from the current _sections.json
    """
    project = unquote(project)
    _validate_project_name(project)
    project = _clean_project_name(project)
    user_id = str(user.get("_id"))
    try:
        docx_path = await rebuild_docx(user_id, project, db, comment=body.comment)
        return {
            "success": True,
            "docx_path": docx_path,
            "download_url": f"/api/download-srs/{project}_SRS",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/history")
async def get_history(
    project: str,
    user=Depends(require_user),
    db=Depends(get_db),
):
    """Return the version list for a project."""
    project = unquote(project)
    _validate_project_name(project)
    project = _clean_project_name(project)
    user_id = str(user.get("_id"))
    history = await get_version_history(user_id, project, db)
    return {"success": True, "versions": history}


@router.post("/{project}/restore")
async def restore(
    project: str,
    body: RestoreRequest,
    user=Depends(require_user),
    db=Depends(get_db),
):
    """Restore a project to a specific version."""
    project = unquote(project)
    _validate_project_name(project)
    project = _clean_project_name(project)
    user_id = str(user.get("_id"))
    try:
        await restore_version(user_id, project, body.version, db)
        return {"success": True, "message": f"Project restored to v{body.version}"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/download-version/{version}")
async def download_version(
    project: str,
    version: int,
    user=Depends(require_user),
    db=Depends(get_db),
):
    """Download a specific historical .docx backup from GridFS."""
    from fastapi.responses import Response

    project = unquote(project)
    _validate_project_name(project)
    project = _clean_project_name(project)
    user_id = str(user.get("_id"))

    fs = FileStorage(db)
    data = await fs.get_file({
        "type": "version_docx",
        "user_id": user_id,
        "project_name": project,
        "version": version
    })

    if not data:
        raise HTTPException(status_code=404, detail=f"Version v{version} document not found")

    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{project}_SRS_v{version}.docx"'}
    )