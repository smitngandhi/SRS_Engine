from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AutomotiveIntroductionSchema(StrictBaseModel):
    section_number: str = Field(default="1", description="Section number")
    section_title: str = Field(default="Introduction & Scope", description="Section title")
    vehicle_system_description: str = Field(..., description="Description of the vehicle and E/E system")
    ee_system_overview: str = Field(..., description="Overview of the Electrical/Electronic system involved")
    software_classification: str = Field(..., description="High-level software classification and role in the vehicle")
    applicable_standards: List[str] = Field(
        ..., description="List of applicable standards (ISO 26262, ASPICE, ISO 21434, etc.)"
    )
    intended_audience: List[str] = Field(..., description="Intended audience for this SRS")
    document_revision: Optional[str] = Field(default=None, description="Document revision number")
