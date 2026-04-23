from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EnergyIntroductionSchema(StrictBaseModel):
    section_number: str = Field(default="1", description="Section number")
    section_title: str = Field(default="Introduction & System Overview", description="Section title")
    utility_type: Literal["Electric", "Gas", "Water", "Multi-Utility"] = Field(
        ..., description="Type of utility this system manages"
    )
    smart_grid_architecture: str = Field(..., description="Description of the smart grid architecture context")
    scada_system_description: str = Field(..., description="Description of the SCADA system integration context")
    applicable_standards: List[str] = Field(
        ..., description="Applicable standards (NERC CIP, IEC 61850, IEEE 1547, etc.)"
    )
    document_purpose: str = Field(..., description="Purpose and scope of this SRS")
    critical_infrastructure_designation: bool = Field(
        ..., description="Whether this system is designated as critical infrastructure"
    )
