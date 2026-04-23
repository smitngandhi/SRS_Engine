from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StructuralCoverageRequirement(StrictBaseModel):
    coverage_type: Literal["Statement", "Decision", "MC/DC"] = Field(
        ..., description="Type of structural coverage required"
    )
    required_for_dal: Literal["Level A", "Level B", "Level C", "Level D"] = Field(
        ..., description="Minimum DAL level that requires this coverage type"
    )
    target_percentage: float = Field(..., description="Required coverage percentage (0-100)")


class VerificationMethod(StrictBaseModel):
    req_id: str = Field(..., description="Requirement ID being verified")
    method: Literal["Analysis", "Review", "Test", "Simulation"] = Field(
        ..., description="Verification method used"
    )
    independence_required: bool = Field(..., description="Whether independent verification is required per DAL")


class AerospaceSoftwareVerificationPlanSchema(StrictBaseModel):
    section_number: str = Field(default="4", description="Section number")
    section_title: str = Field(default="Software Verification Plan", description="Section title")
    verification_methods: List[VerificationMethod]
    requirements_based_testing: bool = Field(
        default=True, description="Whether requirements-based testing is applied"
    )
    structural_coverage: List[StructuralCoverageRequirement]
    robustness_testing_required: bool = Field(
        ..., description="Whether robustness/boundary condition testing is performed"
    )
    independence_criteria: str = Field(
        ..., description="Criteria for independence of verification activities per DO-178C"
    )
    test_environment_description: Optional[str] = Field(
        default=None, description="Description of test environment (target hardware, simulator)"
    )
