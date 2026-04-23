from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AerospaceCertificationBasisSchema(StrictBaseModel):
    section_number: str = Field(default="1", description="Section number")
    section_title: str = Field(default="Introduction & Certification Basis", description="Section title")
    aircraft_system_description: str = Field(..., description="Description of the aircraft system this software is part of")
    software_dal_level: Literal["Level A", "Level B", "Level C", "Level D", "Level E"] = Field(
        ..., description="DO-178C Design Assurance Level (A=Catastrophic to E=No Effect)"
    )
    asil_failure_condition: Literal["Catastrophic", "Hazardous", "Major", "Minor", "No Effect"] = Field(
        ..., description="Failure condition category per ARP4754A that determined the DAL"
    )
    certification_authority: str = Field(..., description="Certifying authority (FAA, EASA, TCCA, etc.)")
    applicable_airworthiness_standards: List[str] = Field(
        ..., description="Applicable airworthiness standards (e.g. FAR 25.1309, CS-25)"
    )
    do_178c_applicable: bool = Field(default=True, description="Whether DO-178C is the applicable software standard")
    additional_standards: Optional[List[str]] = Field(
        default=None, description="Additional applicable standards (DO-254, DO-278A, etc.)"
    )
