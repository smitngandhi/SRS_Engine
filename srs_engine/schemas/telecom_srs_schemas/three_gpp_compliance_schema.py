from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpecificationReference(StrictBaseModel):
    spec_number: str = Field(..., description="3GPP specification number (e.g. TS 23.501)")
    title: str = Field(..., description="Specification title")
    stage: str = Field(..., description="Specification stage (Stage 1, 2, or 3)")
    version: str = Field(..., description="Specification version")
    applicable_sections: Optional[List[str]] = Field(
        default=None, description="Relevant sections or clauses from this specification"
    )


class TelecomThreeGPPComplianceSchema(StrictBaseModel):
    section_number: str = Field(default="2", description="Section number")
    section_title: str = Field(default="3GPP Specification Compliance", description="Section title")
    stage1_specifications: List[SpecificationReference] = Field(
        ..., description="Stage 1 service requirement specifications"
    )
    stage2_specifications: List[SpecificationReference] = Field(
        ..., description="Stage 2 architecture and functional specifications"
    )
    stage3_specifications: List[SpecificationReference] = Field(
        ..., description="Stage 3 protocol implementation specifications"
    )
    conformance_test_specs: Optional[List[str]] = Field(
        default=None, description="Applicable conformance test specifications (TS 38.521, etc.)"
    )
