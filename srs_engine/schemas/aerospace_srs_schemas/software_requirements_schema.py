from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HighLevelRequirement(StrictBaseModel):
    hlr_id: str = Field(..., description="High-level requirement ID (e.g. HLR-001)")
    description: str = Field(..., description="Requirement description")
    is_safety_requirement: bool = Field(..., description="Whether this is a safety-relevant requirement")
    source: Optional[str] = Field(default=None, description="Source of this requirement (system req ID, regulation)")


class LowLevelRequirement(StrictBaseModel):
    llr_id: str = Field(..., description="Low-level requirement ID (e.g. LLR-001)")
    parent_hlr_id: str = Field(..., description="Parent high-level requirement ID")
    description: str = Field(..., description="Detailed requirement description at implementation level")
    is_derived: bool = Field(..., description="Whether this is a derived requirement (no direct HLR parent)")


class InterfaceRequirement(StrictBaseModel):
    icd_ref: str = Field(..., description="Interface Control Document reference")
    source_element: str = Field(..., description="Source element of the interface")
    destination_element: str = Field(..., description="Destination element of the interface")
    data_description: str = Field(..., description="Data or signal description")
    timing_constraints: Optional[str] = Field(default=None, description="Timing constraints on this interface")


class AerospaceSoftwareRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="7", description="Section number")
    section_title: str = Field(default="Software Requirements Specification", description="Section title")
    high_level_requirements: List[HighLevelRequirement]
    low_level_requirements: List[LowLevelRequirement]
    safety_requirements: List[str] = Field(
        ..., description="List of requirement IDs tagged as safety requirements"
    )
    interface_requirements: List[InterfaceRequirement]
    derived_requirements_rationale: Optional[str] = Field(
        default=None, description="Rationale for derived requirements not traceable to system requirements"
    )
