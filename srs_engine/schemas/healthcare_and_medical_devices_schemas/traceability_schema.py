from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class TraceabilityLink(StrictBaseModel):
    """Complete traceability record - TABLE ROW"""
    requirement_id: str = Field(..., description="Requirement ID being traced")
    requirement_type: str = Field(..., description="FR, PR, IF, DS, SR")
    design_elements: List[str] = Field(..., description="Architecture components implementing this")
    risk_controls: List[str] = Field(default_factory=list, description="Risk control IDs if safety-related")
    test_cases: List[str] = Field(..., description="Test case IDs verifying this")
    verification_status: Literal["Not Started", "In Progress", "Complete", "Passed", "Failed"] = Field(..., description="Current status")
    comments: Optional[str] = Field(None, description="Additional notes")


class TraceabilityMatrixSection(StrictBaseModel):
    """
    Render as: TABLE (CRITICAL - Most important regulatory artifact)
    Complete bidirectional traceability
    """
    section_title: str = Field(default="8. TRACEABILITY MATRIX")
    overview: str = Field(..., description="Importance of traceability for compliance")
    traceability_links: List[TraceabilityLink] = Field(..., description="Complete traceability records")
    coverage_summary: str = Field(..., description="Summary of traceability completeness")
    
    # TABLE HEADERS: Req ID | Type | Design Elements | Risk Controls | Test Cases | Status | Comments
    # NOTE: This is the MOST CRITICAL table for FDA/regulatory review
