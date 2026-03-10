from __future__ import annotations

"""
parse_schema.py
───────────────
Pydantic v2 models for the Unified Document JSON produced by the Parser Agent.
This schema is the contract between the Parser and all downstream agents
(Validation Gate → Structure Extraction → Quality → etc.)
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


# ── Table cell / row ─────────────────────────────────────────────────────────

class ParsedTable(BaseModel):
    table_index: int
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    extraction_method: str = "unknown"   # "pdfplumber" | "camelot" | "docx"


# ── Section (recursive for subsections) ──────────────────────────────────────

class ParsedSection(BaseModel):
    section_id: str                          # e.g. "1", "1.2", "3.4.1"
    heading: str
    level: int                               # 1 = top-level, 2 = sub, etc.
    content: str = ""                        # full text under this heading
    tables: list[ParsedTable] = Field(default_factory=list)
    subsections: list["ParsedSection"] = Field(default_factory=list)

ParsedSection.model_rebuild()               # required for self-referencing model


# ── Parse metadata ────────────────────────────────────────────────────────────

class ParseMetadata(BaseModel):
    file_id: str
    original_filename: str
    file_type: str                           # "pdf" | "docx"
    page_count: int | None = None
    word_count: int | None = None
    parsed_at: datetime
    primary_extractor: str                   # e.g. "pdfplumber", "python-docx"
    fallback_used: bool = False
    fallback_extractor: str | None = None
    ocr_used: bool = False
    partial_parse: bool = False              # True if Validation Gate flagged issues but continued
    warnings: list[str] = Field(default_factory=list)


# ── Top-level Unified Document JSON ──────────────────────────────────────────

class UnifiedDocumentJSON(BaseModel):
    metadata: ParseMetadata
    sections: list[ParsedSection] = Field(default_factory=list)
    raw_text: str = ""                       # full concatenated text, for embeddings / fallback
    tables: list[ParsedTable] = Field(default_factory=list)   # top-level tables (outside any section)


# ── API response models ───────────────────────────────────────────────────────

class ParseResponse(BaseModel):
    success: bool
    file_id: str
    parsed_doc_path: str                     # path to saved UnifiedDocumentJSON file
    metadata: ParseMetadata


class ParseStatusResponse(BaseModel):
    file_id: str
    parsed_doc_path: str
    metadata: ParseMetadata
    section_count: int
    top_level_sections: list[str]            # heading titles only, for quick preview