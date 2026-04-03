from __future__ import annotations

"""
schemas/diagram_schemas/diagram_schemas.py
──────────────────────────────────────────
Pydantic schemas for the Diagram Studio API.

v2: Added detail_level, state/gantt/mindmap diagram types, server-side
    verification fields.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Output schemas ─────────────────────────────────────────────────────────────

class DiagramVersion(BaseModel):
    version_id: str
    version_number: int
    prompt: str
    mermaid_code: str
    svg_path: str
    created_at: str  # ISO-8601 string

    @classmethod
    def from_doc(cls, v: dict) -> "DiagramVersion":
        return cls(
            version_id=str(v.get("version_id", "")),
            version_number=v.get("version_number", 1),
            prompt=v.get("prompt", ""),
            mermaid_code=v.get("mermaid_code", ""),
            svg_path=v.get("svg_path", ""),
            created_at=_iso(v.get("created_at")),
        )


class DiagramOut(BaseModel):
    diagram_id: str
    project_name: str
    diagram_type: str
    prompt: str
    current_version: Optional[DiagramVersion]
    versions: List[DiagramVersion]
    created_at: str
    updated_at: str

    @classmethod
    def from_doc(cls, doc: dict) -> "DiagramOut":
        if doc is None:
            raise ValueError("Cannot build DiagramOut from None document")

        versions = [DiagramVersion.from_doc(v) for v in doc.get("versions", [])]
        current = versions[-1] if versions else None

        return cls(
            diagram_id=str(doc.get("diagram_id", "")),
            project_name=doc.get("project_name", ""),
            diagram_type=doc.get("diagram_type", "flowchart"),
            prompt=doc.get("prompt", ""),
            current_version=current,
            versions=versions,
            created_at=_iso(doc.get("created_at")),
            updated_at=_iso(doc.get("updated_at")),
        )

    def dict(self, **kwargs):  # noqa: A003
        d = super().dict(**kwargs)
        if self.current_version:
            d["current_version"] = self.current_version.dict()
        d["versions"] = [v.dict() for v in self.versions]
        return d


def _iso(dt) -> str:
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return (dt.isoformat() + "Z").replace("+00:00Z", "Z")
    return str(dt)


# ── Request schemas ────────────────────────────────────────────────────────────

# Supported diagram types for technical projects
VALID_DIAGRAM_TYPES = frozenset({
    "flowchart",   # System / process flow
    "sequence",    # API / service interaction
    "erd",         # Database schema
    "class",       # Object model / architecture
    "state",       # State machine / lifecycle
    "gantt",       # Project / sprint timeline
    "mindmap",     # Feature / requirement map
    "custom",      # Let the LLM pick the best type
})

# Detail levels control verbosity and node density
VALID_DETAIL_LEVELS = frozenset({"brief", "standard", "detailed", "comprehensive"})


class DiagramGenerateRequest(BaseModel):
    project_name: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    diagram_type: str = Field(default="flowchart")
    detail_level: str = Field(
        default="standard",
        description="brief | standard | detailed | comprehensive",
    )
    selected_document_ids: List[str] = Field(default_factory=list)
    error_feedback: str = Field(default="")

    class Config:
        extra = "allow"   # forward-compatibility: ignore unknown fields


class DiagramRegenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    diagram_type: str = Field(default="flowchart")
    detail_level: str = Field(default="standard")
    selected_document_ids: List[str] = Field(default_factory=list)
    error_feedback: str = Field(default="")

    class Config:
        extra = "allow"


class DiagramEditRequest(BaseModel):
    mermaid_code: str = Field(..., min_length=1)