from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CodingStandardCompliance(StrictBaseModel):
    standard_name: str = Field(..., description="Coding standard name (MISRA C 2012, AUTOSAR C++14, CERT C)")
    version: str = Field(..., description="Version of the coding standard")
    deviations_allowed: bool = Field(..., description="Whether deviations from the standard are allowed")
    deviation_process: Optional[str] = Field(default=None, description="Process for documenting and approving deviations")
    enforcement_tool: Optional[str] = Field(default=None, description="Static analysis tool enforcing this standard (PC-lint, LDRA, etc.)")


class AutomotiveCodingStandardsSchema(StrictBaseModel):
    section_number: str = Field(default="9", description="Section number")
    section_title: str = Field(default="Coding Standards Compliance", description="Section title")
    coding_standards: List[CodingStandardCompliance]
    static_analysis_mandatory: bool = Field(..., description="Whether static analysis is mandated")
    dynamic_analysis_required: bool = Field(..., description="Whether dynamic analysis (e.g. runtime checks) is required")
