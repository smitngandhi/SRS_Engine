from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DiagramGenerateRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=120)
    prompt: str = Field(..., min_length=5, max_length=2000)
    diagram_type: str = Field(default="flowchart")  # flowchart | sequence | erd | class | custom
    # Context Selector: optional list of parsed document IDs to use as context
    selected_document_ids: list[str] = Field(default_factory=list)
    # Retry loop: previous Mermaid parse error to feed back to the LLM
    error_feedback: str = Field(default="")


class DiagramRegenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=2000)
    diagram_type: str = Field(default="flowchart")
    # Context Selector: optional list of parsed document IDs to use as context
    selected_document_ids: list[str] = Field(default_factory=list)
    # Retry loop: previous Mermaid parse error to feed back to the LLM
    error_feedback: str = Field(default="")



class DiagramEditRequest(BaseModel):
    mermaid_code: str = Field(..., min_length=3)


class DiagramVersionOut(BaseModel):
    version_id: str
    version_number: int
    prompt: str
    mermaid_code: str
    svg_path: str
    created_at: datetime


class DiagramOut(BaseModel):
    diagram_id: str
    project_name: str
    diagram_type: str
    created_at: datetime
    updated_at: datetime
    versions: list[DiagramVersionOut]
    current_version: Optional[DiagramVersionOut] = None

    @classmethod
    def from_doc(cls, doc: dict) -> "DiagramOut":
        """
        Build a DiagramOut from a raw MongoDB document.

        svg_path stored in MongoDB is now always a public URL
        (e.g. /static/diagrams/user/diag/v1.svg) so no path
        transformation is required here.

        If you have OLD documents in the DB that still contain
        filesystem paths, the fallback block below converts them.
        """
        versions = []
        for v in doc.get("versions", []):
            sp = v.get("svg_path", "")

            # ── Backwards-compat: convert legacy filesystem paths → URL ─────────
            # New documents always store a URL, so this block is a no-op for them.
            if sp and not sp.startswith("/static"):
                # Normalise separators first (Windows backslashes)
                sp = sp.replace("\\", "/")
                # Strip leading './'
                if sp.startswith("./"):
                    sp = sp[2:]
                # Convert  srs_engine/static/diagrams/...  → /static/diagrams/...
                if "srs_engine/static" in sp:
                    sp = "/static" + sp.split("srs_engine/static")[1]
                elif not sp.startswith("/"):
                    sp = "/" + sp

            v["svg_path"] = sp
            versions.append(DiagramVersionOut(**v))

        current = versions[-1] if versions else None
        return cls(
            diagram_id=doc["diagram_id"],
            project_name=doc["project_name"],
            diagram_type=doc.get("diagram_type", "custom"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            versions=versions,
            current_version=current,
        )