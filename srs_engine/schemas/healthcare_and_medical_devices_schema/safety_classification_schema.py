from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthcareSafetyClassificationSchema(StrictBaseModel):
    section_number: str = Field(default="2", description="Section number")
    section_title: str = Field(default="Software Safety Classification", description="Section title")
    safety_class: Literal["Class A", "Class B", "Class C"] = Field(
        ..., description="IEC 62304 software safety class assigned to the software"
    )
    classification_rationale: str = Field(
        ..., description="Rationale justifying the chosen safety class"
    )
    injury_potential: Optional[str] = Field(
        default=None, description="Description of potential injury if the software fails"
    )
    severity_of_harm: Optional[Literal["No Injury", "Non-Serious Injury", "Serious Injury or Death"]] = Field(
        default=None, description="Maximum severity of harm if the software fails"
    )