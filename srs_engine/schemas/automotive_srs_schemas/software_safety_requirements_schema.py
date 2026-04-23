from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SoftwareSafetyRequirement(StrictBaseModel):
    ssr_id: str = Field(..., description="Software safety requirement ID (e.g. SSR-001)")
    parent_tsr_id: str = Field(..., description="Parent technical safety requirement ID")
    description: str = Field(..., description="Software safety requirement description")
    asil: Literal["QM", "A", "B", "C", "D"] = Field(..., description="ASIL level")
    freedom_from_interference: bool = Field(..., description="Whether FFI measures are required for this requirement")


class ASILDecomposition(StrictBaseModel):
    original_req_id: str = Field(..., description="Original requirement ID being decomposed")
    original_asil: Literal["B", "C", "D"] = Field(..., description="Original ASIL level being decomposed")
    channel_a_req_id: str = Field(..., description="Requirement ID for channel A after decomposition")
    channel_a_asil: str = Field(..., description="ASIL level assigned to channel A (e.g. ASIL A(D))")
    channel_b_req_id: str = Field(..., description="Requirement ID for channel B after decomposition")
    channel_b_asil: str = Field(..., description="ASIL level assigned to channel B (e.g. ASIL A(D))")
    decomposition_rationale: str = Field(..., description="Rationale for this ASIL decomposition")


class AutomotiveSoftwareSafetyRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="4", description="Section number")
    section_title: str = Field(default="Software Safety Requirements", description="Section title")
    software_safety_requirements: List[SoftwareSafetyRequirement]
    asil_decompositions: Optional[List[ASILDecomposition]] = Field(
        default=None, description="ASIL decompositions applied to requirements"
    )
    ffi_requirements: Optional[List[str]] = Field(
        default=None, description="Freedom from Interference requirements and measures"
    )
