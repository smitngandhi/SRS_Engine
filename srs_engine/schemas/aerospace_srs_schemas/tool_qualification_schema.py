from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QualifiedTool(StrictBaseModel):
    tool_name: str = Field(..., description="Name of the tool requiring qualification")
    version: str = Field(..., description="Tool version being qualified")
    tql_level: Literal["TQL-1", "TQL-2", "TQL-3", "TQL-4", "TQL-5"] = Field(
        ..., description="DO-330 Tool Qualification Level (TQL-1=highest rigor to TQL-5=lowest)"
    )
    tool_operational_requirements: List[str] = Field(
        ..., description="Requirements the tool must satisfy during operation"
    )
    verification_procedures: List[str] = Field(
        ..., description="Procedures used to verify the tool meets its requirements"
    )
    qualification_rationale: str = Field(..., description="Rationale for the assigned TQL level")


class AerospaceToolQualificationSchema(StrictBaseModel):
    section_number: str = Field(default="9", description="Section number")
    section_title: str = Field(default="Tool Qualification (DO-330)", description="Section title")
    qualified_tools: List[QualifiedTool]
    tool_qualification_plan_reference: Optional[str] = Field(
        default=None, description="Reference to the Tool Qualification Plan document"
    )
