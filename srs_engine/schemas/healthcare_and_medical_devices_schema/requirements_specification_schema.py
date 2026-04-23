from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FunctionalRequirement(StrictBaseModel):
    req_id: str = Field(..., description="Unique requirement ID (e.g. FR-001)")
    description: str = Field(..., description="Clear, testable action the software must perform")
    priority: Literal["Shall", "Should", "May"] = Field(..., description="Requirement priority level")
    linked_risk_id: Optional[str] = Field(default=None, description="Linked risk ID from ISO 14971 risk analysis")


class PerformanceRequirement(StrictBaseModel):
    req_id: str = Field(..., description="Unique requirement ID (e.g. PERF-001)")
    metric: str = Field(..., description="Performance metric (response time, accuracy, uptime)")
    target_value: str = Field(..., description="Target value or threshold")
    measurement_method: Optional[str] = Field(default=None, description="How this metric will be measured")


class InterfaceRequirement(StrictBaseModel):
    interface_type: Literal["User Interface", "API", "Communication Standard", "Hardware"] = Field(
        ..., description="Type of interface"
    )
    description: str = Field(..., description="Description of the interface requirement")
    standard_used: Optional[str] = Field(default=None, description="Standard used e.g. HL7, FHIR, DICOM")


class DataSecurityPrivacy(StrictBaseModel):
    phi_pii_handling: str = Field(..., description="Description of PHI/PII handling approach")
    applicable_regulations: List[str] = Field(..., description="Applicable regulations (HIPAA, GDPR, etc.)")
    encryption_requirements: Optional[str] = Field(default=None, description="Encryption requirements for data at rest and in transit")
    access_control_requirements: Optional[str] = Field(default=None, description="Access control and authentication requirements")


class SafetyRiskControlRequirement(StrictBaseModel):
    req_id: str = Field(..., description="Unique requirement ID (e.g. SRISK-001)")
    linked_hazard_id: str = Field(..., description="Linked hazard ID from ISO 14971 analysis")
    description: str = Field(..., description="Software control that mitigates the linked risk")
    control_type: Literal["Prevention", "Detection", "Mitigation"] = Field(..., description="Type of risk control")


class HealthcareRequirementsSpecificationSchema(StrictBaseModel):
    section_number: str = Field(default="4", description="Section number")
    section_title: str = Field(default="Requirements Specification", description="Section title")
    functional_requirements: List[FunctionalRequirement]
    performance_requirements: List[PerformanceRequirement]
    interface_requirements: List[InterfaceRequirement]
    data_security_privacy: DataSecurityPrivacy
    safety_risk_control_requirements: List[SafetyRiskControlRequirement]