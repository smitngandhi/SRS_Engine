from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SupportingDocument(StrictBaseModel):
    """Reference to supporting document - TABLE ROW"""
    document_id: str = Field(..., description="Unique document identifier")
    document_title: str = Field(..., description="Full document title")
    document_type: str = Field(..., description="SOP, Plan, Report, Specification, etc.")
    version: str = Field(..., description="Document version")
    location: str = Field(..., description="Where document is stored")
    relevance: str = Field(..., description="Why this document is referenced")


class AppendicesSection(StrictBaseModel):
    """
    Render as: TABLE
    Supporting documentation references
    """
    section_title: str = Field(default="9. APPENDICES")
    title: str = Field(default="9.1 Supporting Documents List")
    overview: str = Field(..., description="Overview of supporting documentation")
    supporting_documents: List[SupportingDocument] = Field(..., description="All referenced documents")
    
    # TABLE HEADERS: Doc ID | Title | Type | Version | Location | Relevance