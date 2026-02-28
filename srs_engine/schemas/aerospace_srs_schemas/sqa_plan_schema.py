from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuditActivity(StrictBaseModel):
    audit_type: str = Field(..., description="Type of audit (process audit, product audit, conformance review)")
    frequency: str = Field(..., description="Frequency of this audit activity")
    responsible_party: str = Field(..., description="Who performs this audit")


class AerospaceSQAPlanSchema(StrictBaseModel):
    section_number: str = Field(default="6", description="Section number")
    section_title: str = Field(default="Software Quality Assurance Plan", description="Section title")
    qaa_activities: List[str] = Field(..., description="Quality assurance activities performed")
    audits: List[AuditActivity]
    problem_reporting_procedure: str = Field(..., description="Procedure for reporting and tracking software problems")
    conformance_review_process: str = Field(..., description="Process for software conformance review prior to certification")
    transition_criteria: Optional[List[str]] = Field(
        default=None, description="Criteria for transitioning between lifecycle phases"
    )
