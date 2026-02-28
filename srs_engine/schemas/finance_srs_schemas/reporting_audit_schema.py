from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegulatoryReport(StrictBaseModel):
    report_name: str = Field(..., description="Name of regulatory report (SAR, CTR, Form 8300, etc.)")
    reporting_authority: str = Field(..., description="Regulatory body the report is submitted to (FinCEN, SEC, FINRA)")
    trigger_condition: str = Field(..., description="Condition that triggers this report")
    submission_deadline: Optional[str] = Field(default=None, description="Deadline for submission (e.g. 30 days)")
    automated: bool = Field(..., description="Whether reporting is automated or manual")


class AuditTrailRequirement(StrictBaseModel):
    event_type: str = Field(..., description="Type of event captured in audit trail")
    data_captured: List[str] = Field(..., description="Fields captured for this event (timestamp, user, action, etc.)")
    retention_period: str = Field(..., description="How long audit records are retained")
    tamper_proof: bool = Field(..., description="Whether audit logs are tamper-proof/immutable")


class FinanceReportingAuditSchema(StrictBaseModel):
    section_number: str = Field(default="5", description="Section number")
    section_title: str = Field(default="Reporting & Audit Requirements", description="Section title")
    regulatory_reports: List[RegulatoryReport]
    audit_trail: List[AuditTrailRequirement]
    financial_disclosure_requirements: Optional[List[str]] = Field(
        default=None, description="Financial disclosure obligations"
    )
    sox_controls: Optional[List[str]] = Field(
        default=None, description="SOX controls for data integrity (if applicable)"
    )
