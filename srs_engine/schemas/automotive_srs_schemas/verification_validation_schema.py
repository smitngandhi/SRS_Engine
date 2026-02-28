from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CodeCoverageRequirement(StrictBaseModel):
    asil: Literal["A", "B", "C", "D"] = Field(..., description="ASIL level")
    statement_coverage: bool = Field(..., description="Whether statement coverage is required")
    branch_coverage: bool = Field(..., description="Whether branch coverage is required")
    mc_dc_coverage: bool = Field(..., description="Whether MC/DC coverage is required")
    target_percentage: float = Field(..., description="Required coverage percentage")


class TestLevel(StrictBaseModel):
    level: Literal["Unit", "Integration", "System", "Regression", "HIL", "SIL"] = Field(
        ..., description="Test level"
    )
    description: str = Field(..., description="Description of testing activities at this level")
    tools_used: Optional[List[str]] = Field(default=None, description="Testing tools used at this level")
    asil_applicable: Optional[str] = Field(default=None, description="ASIL levels requiring this test level")


class AutomotiveVerificationValidationSchema(StrictBaseModel):
    section_number: str = Field(default="8", description="Section number")
    section_title: str = Field(default="Verification & Validation", description="Section title")
    test_levels: List[TestLevel]
    code_coverage_requirements: List[CodeCoverageRequirement]
    requirements_traceability_tool: Optional[str] = Field(
        default=None, description="Tool used for requirements traceability (DOORS, Jama, etc.)"
    )
    regression_strategy: Optional[str] = Field(
        default=None, description="Regression testing strategy"
    )
