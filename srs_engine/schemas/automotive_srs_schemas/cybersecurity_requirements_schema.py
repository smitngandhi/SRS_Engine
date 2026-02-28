from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TARAEntry(StrictBaseModel):
    asset_id: str = Field(..., description="Asset identifier")
    asset_description: str = Field(..., description="Description of the asset to be protected")
    threat_description: str = Field(..., description="Threat scenario description")
    attack_path: str = Field(..., description="Attack path or attack vector")
    impact: Literal["Severe", "Major", "Moderate", "Negligible"] = Field(..., description="Impact rating")
    feasibility: Literal["High", "Medium", "Low", "Very Low"] = Field(..., description="Attack feasibility rating")
    car_level: Literal["CAL 1", "CAL 2", "CAL 3", "CAL 4"] = Field(
        ..., description="Cybersecurity Assurance Level assigned"
    )


class CybersecurityGoal(StrictBaseModel):
    csg_id: str = Field(..., description="Cybersecurity goal ID")
    description: str = Field(..., description="Cybersecurity goal statement")
    linked_tara_ids: List[str] = Field(..., description="TARA entry IDs this goal addresses")
    cal_level: Literal["CAL 1", "CAL 2", "CAL 3", "CAL 4"] = Field(..., description="CAL level for this goal")


class SecureCommunicationRequirement(StrictBaseModel):
    req_id: str = Field(..., description="Secure communication requirement ID")
    interface: str = Field(..., description="Communication interface or bus")
    security_mechanism: str = Field(..., description="Security mechanism used (MAC, encryption, SecOC)")
    authentication_protocol: Optional[str] = Field(default=None, description="Authentication protocol if applicable")


class AutomotiveCybersecurityRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="6", description="Section number")
    section_title: str = Field(default="Cybersecurity Requirements (ISO 21434)", description="Section title")
    tara_entries: List[TARAEntry]
    cybersecurity_goals: List[CybersecurityGoal]
    cybersecurity_requirements: List[str] = Field(
        ..., description="List of derived cybersecurity requirement descriptions"
    )
    secure_communication_requirements: List[SecureCommunicationRequirement]
