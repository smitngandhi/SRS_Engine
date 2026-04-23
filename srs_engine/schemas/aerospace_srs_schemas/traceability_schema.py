from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TraceabilityEntry(StrictBaseModel):
    system_req_id: Optional[str] = Field(default=None, description="System requirement ID (ARP4754A level)")
    hlr_id: Optional[str] = Field(default=None, description="High-level software requirement ID")
    llr_id: Optional[str] = Field(default=None, description="Low-level software requirement ID")
    design_element: Optional[str] = Field(default=None, description="Software design element or component")
    source_code_ref: Optional[str] = Field(default=None, description="Source code file/function reference")
    test_case_id: Optional[str] = Field(default=None, description="Test case ID verifying this requirement")
    coverage_status: Optional[str] = Field(default=None, description="Structural coverage status (Statement, Decision, MC/DC)")


class AerospaceTraceabilitySchema(StrictBaseModel):
    section_number: str = Field(default="10", description="Section number")
    section_title: str = Field(default="Bidirectional Traceability", description="Section title")
    entries: List[TraceabilityEntry]
    traceability_tool: Optional[str] = Field(
        default=None, description="Tool used to maintain traceability (DOORS, Jama, etc.)"
    )
