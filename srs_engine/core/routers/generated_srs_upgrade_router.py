"""
core/routers/generated_srs_upgrade_router.py
────────────────────────────────────────────
API routes for upgrading SRS documents generated on this platform.

Completely separate from the existing upload-based upgrade_router.py.
"""

from __future__ import annotations

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
from srs_engine.core.services.generated_srs_upgrade_service import BASE_DIR as GENERATED_DIR


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


router = APIRouter(prefix="/upgrade/generated", tags=["generated-upgrade"])


# ── Shared guard ──────────────────────────────────────────────────────────────

def _validate_project_name(project: str) -> None:
    """
    Reject project names that contain path-traversal sequences.

    BUG FIX: download_version (and other project-scoped endpoints) accepted
    the raw `project` URL parameter and passed it straight into a Path
    construction:
        GENERATED_DIR / user_id / f"{project}_SRS_v{version}.docx"
    A crafted project name containing ".." could escape the user's directory
    and read arbitrary files from the server.  Every other download endpoint
    in the codebase has an equivalent guard; this one was missing it.
    """
    if not project or "/" in project or "\\" in project or ".." in project:
        raise HTTPException(status_code=400, detail="Invalid project name")


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
async def list_docs(user=Depends(require_user)):
    """List all generated SRS documents for the logged-in user."""
    user_id = str(user.get("_id"))
    docs = await list_generated_srs(user_id)
    return {"success": True, "documents": docs}


@router.get("/{project}/section/{page_index}")
async def get_section(
    project: str,
    page_index: int,
    user=Depends(require_user),
):
    """
    Fast path: look up a section by page_index.
    Returns 404 if page_index is not in the domain's map.
    """
    _validate_project_name(project)
    user_id = str(user.get("_id"))
    try:
        result = await get_section_by_pageindex(user_id, project, page_index)
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
):
    """
    RAG fallback: search for the most relevant section using FAISS.
    Returns the matched section + confidence score.
    """
    _validate_project_name(project)
    user_id = str(user.get("_id"))
    try:
        result = await search_section_rag(user_id, project, body.query)
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
):
    """
    Call the upgrade agent and return a preview (original + upgraded JSON).
    Does NOT persist any changes.
    """
    _validate_project_name(project)
    user_id = str(user.get("_id"))
    try:
        result = await preview_upgrade(
            user_id=user_id,
            project_name=project,
            page_index=page_index,
            instruction=body.instruction,
            lookup_method=body.lookup_method,
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
):
    """
    Persist the upgraded section JSON.
    Creates a versioned backup before writing.
    """
    _validate_project_name(project)
    user_id = str(user.get("_id"))
    try:
        await confirm_upgrade(
            user_id=user_id,
            project_name=project,
            page_index=page_index,
            upgraded_json=body.upgraded_json,
        )
        return {"success": True, "message": "Section upgraded and saved."}
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project}/rebuild")
async def rebuild(
    project: str,
    body: RebuildRequest,
    user=Depends(require_user),
):
    """
    Rebuild the .docx from the current _sections.json
    (mix of original + confirmed upgrades).
    """
    _validate_project_name(project)
    user_id = str(user.get("_id"))
    try:
        docx_path = await rebuild_docx(user_id, project, comment=body.comment)
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
):
    """Return the version list for a project."""
    _validate_project_name(project)
    user_id = str(user.get("_id"))
    history = await get_version_history(user_id, project)
    return {"success": True, "versions": history}


@router.post("/{project}/restore")
async def restore(
    project: str,
    body: RestoreRequest,
    user=Depends(require_user),
):
    """Restore a project to a specific version."""
    _validate_project_name(project)
    user_id = str(user.get("_id"))
    try:
        await restore_version(user_id, project, body.version)
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
):
    """Download a specific historical .docx backup."""
    from fastapi.responses import FileResponse

    # BUG FIX: The original endpoint had no path-traversal guard on `project`.
    # Every other download endpoint in the codebase (download_srs in pages.py,
    # the upload-based upgrader) checks for "..", "/" and "\\" before building
    # a file path. This one was missing the check entirely, allowing a crafted
    # project name to escape the user's directory.
    _validate_project_name(project)

    user_id = str(user.get("_id"))

    file_path = GENERATED_DIR / user_id / f"{project}_SRS_v{version}.docx"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Version v{version} document not found")

    return FileResponse(
        path=str(file_path),
        filename=f"{project}_SRS_v{version}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )