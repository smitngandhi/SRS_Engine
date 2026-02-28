from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BackupRecoveryProcedure(StrictBaseModel):
    backup_type: str = Field(..., description="Type of backup (full, incremental, differential)")
    backup_frequency: str = Field(..., description="How often backups are taken")
    rto_hours: Optional[float] = Field(default=None, description="Recovery Time Objective in hours")
    rpo_hours: Optional[float] = Field(default=None, description="Recovery Point Objective in hours")
    backup_location: Optional[str] = Field(default=None, description="Backup storage location (on-site, cloud, geo-redundant)")


class FailoverMechanism(StrictBaseModel):
    failover_type: str = Field(..., description="Type of failover (active-active, active-passive, hot standby)")
    automatic_failover: bool = Field(..., description="Whether failover is automated")
    failover_time_seconds: Optional[int] = Field(default=None, description="Expected failover time in seconds")


class DataRetentionPolicy(StrictBaseModel):
    data_category: str = Field(..., description="Category of data (transaction records, audit logs, KYC documents)")
    retention_period: str = Field(..., description="Retention period (e.g. 7 years)")
    regulatory_basis: Optional[str] = Field(default=None, description="Regulation requiring this retention period")
    deletion_method: Optional[str] = Field(default=None, description="Method for secure data deletion after retention period")


class IncidentResponseProcedure(StrictBaseModel):
    incident_type: str = Field(..., description="Type of incident (data breach, system outage, fraud event)")
    response_steps: List[str] = Field(..., description="Steps to respond to this incident type")
    notification_requirements: Optional[List[str]] = Field(
        default=None, description="Regulatory notification requirements for this incident"
    )
    escalation_path: Optional[str] = Field(default=None, description="Escalation path for this incident type")


class FinanceBusinessContinuitySchema(StrictBaseModel):
    section_number: str = Field(default="7", description="Section number")
    section_title: str = Field(default="Business Continuity & Disaster Recovery", description="Section title")
    backup_recovery: BackupRecoveryProcedure
    failover_mechanisms: List[FailoverMechanism]
    data_retention_policies: List[DataRetentionPolicy]
    incident_response: List[IncidentResponseProcedure]
