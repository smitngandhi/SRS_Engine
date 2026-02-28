from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HARAItem(StrictBaseModel):
    hara_id: str = Field(..., description="HARA item ID (e.g. HARA-001)")
    hazard_description: str = Field(..., description="Description of the hazardous event")
    operational_situation: str = Field(..., description="Operational situation in which hazard is relevant")
    severity: Literal["S0", "S1", "S2", "S3"] = Field(..., description="Severity class (S0=No Injury to S3=Life Threatening)")
    exposure: Literal["E0", "E1", "E2", "E3", "E4"] = Field(..., description="Exposure class (E0=Incredible to E4=High Probability)")
    controllability: Literal["C0", "C1", "C2", "C3"] = Field(..., description="Controllability class (C0=Controllable to C3=Difficult)")
    asil: Literal["QM", "A", "B", "C", "D"] = Field(..., description="Resulting ASIL level")


class SafetyGoal(StrictBaseModel):
    sg_id: str = Field(..., description="Safety goal ID (e.g. SG-001)")
    linked_hara_id: str = Field(..., description="HARA item this safety goal addresses")
    description: str = Field(..., description="Safety goal statement")
    asil: Literal["QM", "A", "B", "C", "D"] = Field(..., description="ASIL level of this safety goal")
    safe_state: Optional[str] = Field(default=None, description="Safe state the system must reach on failure")


class FunctionalSafetyRequirement(StrictBaseModel):
    fsr_id: str = Field(..., description="Functional safety requirement ID (e.g. FSR-001)")
    linked_sg_id: str = Field(..., description="Safety goal ID this requirement implements")
    description: str = Field(..., description="Functional safety requirement statement")
    asil: Literal["QM", "A", "B", "C", "D"] = Field(..., description="ASIL level")


class AutomotiveFunctionalSafetyConceptSchema(StrictBaseModel):
    section_number: str = Field(default="2", description="Section number")
    section_title: str = Field(default="Functional Safety Concept (ISO 26262)", description="Section title")
    hara_items: List[HARAItem]
    safety_goals: List[SafetyGoal]
    functional_safety_requirements: List[FunctionalSafetyRequirement]
    technical_safety_requirements: Optional[List[str]] = Field(
        default=None, description="Technical safety requirements derived from functional safety requirements"
    )
