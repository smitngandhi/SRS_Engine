from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Hazard(StrictBaseModel):
    hazard_id: str = Field(..., description="Unique hazard identifier (e.g. HAZ-001)")
    hazard_description: str = Field(..., description="Description of the identified hazard")
    hazardous_situation: str = Field(..., description="Sequence of events leading to harm")
    foreseeable_harm: str = Field(..., description="Harm that could result")
    severity: Literal["Negligible", "Minor", "Serious", "Critical", "Catastrophic"] = Field(
        ..., description="Severity of harm per ISO 14971"
    )
    probability: Literal["Improbable", "Remote", "Occasional", "Probable", "Frequent"] = Field(
        ..., description="Probability of harm occurrence"
    )
    risk_level: Literal["Acceptable", "ALARP", "Unacceptable"] = Field(
        ..., description="Initial risk level before controls"
    )


class RiskControlMeasure(StrictBaseModel):
    control_id: str = Field(..., description="Unique control measure ID (e.g. CTRL-001)")
    linked_hazard_id: str = Field(..., description="Hazard ID this control mitigates")
    linked_requirement_id: str = Field(..., description="Requirement ID implementing this control")
    control_description: str = Field(..., description="How this control reduces the risk")
    residual_risk: Literal["Acceptable", "ALARP"] = Field(..., description="Risk level after control application")


class SOUPItem(StrictBaseModel):
    soup_name: str = Field(..., description="Name of the SOUP / off-the-shelf software component")
    version: str = Field(..., description="Version of the SOUP item")
    manufacturer: Optional[str] = Field(default=None, description="Manufacturer or source")
    identified_risks: List[str] = Field(..., description="Risks introduced by this SOUP item")
    controls_applied: List[str] = Field(..., description="Controls applied to mitigate SOUP risks")


class HealthcareHazardRiskAnalysisSchema(StrictBaseModel):
    section_number: str = Field(default="6", description="Section number")
    section_title: str = Field(default="Hazard & Risk Analysis Results", description="Section title")
    hazards: List[Hazard]
    risk_control_measures: List[RiskControlMeasure]
    soup_analysis: List[SOUPItem]