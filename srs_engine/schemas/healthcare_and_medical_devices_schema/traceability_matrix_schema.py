from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TraceabilityEntry(StrictBaseModel):
    requirement_id: str = Field(..., description="Software requirement ID")
    requirement_description: str = Field(..., description="Brief description of the requirement")
    design_element_id: Optional[str] = Field(default=None, description="Design element / architecture component ID")
    risk_control_id: Optional[str] = Field(default=None, description="Risk control measure ID from ISO 14971 analysis")
    test_id: Optional[str] = Field(default=None, description="Test case or test method ID verifying this requirement")
    verification_status: Optional[str] = Field(default=None, description="Current verification status (Pending, Pass, Fail)")


class HealthcareTraceabilityMatrixSchema(StrictBaseModel):
    section_number: str = Field(default="8", description="Section number")
    section_title: str = Field(default="Traceability Matrix", description="Section title")
    entries: List[TraceabilityEntry]