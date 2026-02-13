from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FunctionalRequirement(StrictBaseModel):
    """Individual functional requirement - TABLE ROW"""
    req_id: str = Field(..., description="Unique requirement ID (FR-001)")
    requirement_text: str = Field(..., description="Clear, testable requirement statement")
    rationale: str = Field(..., description="Why this requirement exists")
    priority: Literal["Critical", "High", "Medium", "Low"] = Field(..., description="Implementation priority")
    safety_related: bool = Field(..., description="Is this safety-critical?")
    verification_method: str = Field(..., description="Test, Analysis, Inspection, Demonstration")
    acceptance_criteria: str = Field(..., description="How to verify this requirement is met")


class FunctionalRequirementsSection(StrictBaseModel):
    """
    Render as: TABLE
    Core requirements that define what software must do
    """
    title: str = Field(default="4.1 Functional Requirements")
    overview: str = Field(..., description="Introduction to functional requirements")
    requirements: List[FunctionalRequirement] = Field(..., description="All functional requirements")
    
    # TABLE HEADERS: Req ID | Requirement | Rationale | Priority | Safety? | Verification | Acceptance


class PerformanceRequirement(StrictBaseModel):
    """Performance and reliability requirement - TABLE ROW"""
    req_id: str = Field(..., description="Unique requirement ID (PR-001)")
    performance_metric: str = Field(..., description="What is being measured")
    target_value: str = Field(..., description="Required performance target")
    measurement_method: str = Field(..., description="How to measure this metric")
    acceptable_range: str = Field(..., description="Min/max acceptable values")
    conditions: str = Field(..., description="Under what conditions this applies")


class PerformanceRequirementsSection(StrictBaseModel):
    """
    Render as: TABLE
    Quantifiable performance targets
    """
    title: str = Field(default="4.2 Performance & Reliability Requirements")
    overview: str = Field(..., description="Performance expectations overview")
    requirements: List[PerformanceRequirement] = Field(..., description="Performance specifications")
    
    # TABLE HEADERS: Req ID | Metric | Target | Measurement | Range | Conditions


class InterfaceRequirement(StrictBaseModel):
    """Interface specification - TABLE ROW"""
    req_id: str = Field(..., description="Unique requirement ID (IF-001)")
    interface_type: Literal["User Interface", "Hardware Interface", "Software Interface", "Communication Interface"] = Field(..., description="Type of interface")
    interface_name: str = Field(..., description="Name of the interface")
    description: str = Field(..., description="Interface functionality and behavior")
    protocol_standard: Optional[str] = Field(None, description="HL7, FHIR, DICOM, REST, etc.")
    data_format: Optional[str] = Field(None, description="JSON, XML, CSV, etc.")
    error_handling: str = Field(..., description="How errors are managed")


class InterfaceRequirementsSection(StrictBaseModel):
    """
    Render as: TABLE
    All system interfaces
    """
    title: str = Field(default="4.3 Interface Requirements")
    overview: str = Field(..., description="Interface architecture overview")
    user_interface_requirements: List[InterfaceRequirement] = Field(default_factory=list, description="UI requirements")
    system_interface_requirements: List[InterfaceRequirement] = Field(default_factory=list, description="System-to-system interfaces")
    
    # TABLE HEADERS: Req ID | Type | Name | Description | Protocol | Format | Error Handling


class DataSecurityRequirement(StrictBaseModel):
    """Security and privacy requirement - TABLE ROW"""
    req_id: str = Field(..., description="Unique requirement ID (DS-001)")
    security_control: str = Field(..., description="Type of security control")
    requirement_text: str = Field(..., description="What must be protected and how")
    compliance_standard: str = Field(..., description="HIPAA, GDPR, FDA Cybersecurity, etc.")
    data_classification: str = Field(..., description="PHI, PII, Device Data, etc.")
    implementation: str = Field(..., description="How this is implemented")
    verification: str = Field(..., description="How compliance is verified")


class DataSecuritySection(StrictBaseModel):
    """
    Render as: TABLE
    Critical for regulatory compliance
    """
    title: str = Field(default="4.4 Data Security & Privacy Requirements")
    security_overview: str = Field(..., description="Overall security architecture approach")
    applicable_regulations: List[str] = Field(..., description="HIPAA, GDPR, etc.")
    requirements: List[DataSecurityRequirement] = Field(..., description="Specific security requirements")
    
    # TABLE HEADERS: Req ID | Control | Requirement | Standard | Data Type | Implementation | Verification


class SafetyRiskRequirement(StrictBaseModel):
    """Safety requirement derived from risk analysis - TABLE ROW"""
    req_id: str = Field(..., description="Unique requirement ID (SR-001)")
    related_hazard_id: str = Field(..., description="Reference to hazard in risk analysis")
    risk_control_measure: str = Field(..., description="How software mitigates this risk")
    requirement_text: str = Field(..., description="Specific safety requirement")
    residual_risk: str = Field(..., description="Remaining risk after control")
    verification_method: str = Field(..., description="How control is verified")


class SafetyRiskRequirementsSection(StrictBaseModel):
    """
    Render as: TABLE
    Links requirements directly to risk controls (ISO 14971)
    """
    title: str = Field(default="4.5 Safety & Risk Control Requirements")
    overview: str = Field(..., description="How requirements address identified risks")
    requirements: List[SafetyRiskRequirement] = Field(..., description="Safety-related requirements")
    
    # TABLE HEADERS: Req ID | Hazard ID | Control Measure | Requirement | Residual Risk | Verification


class RequirementsSpecificationSection(StrictBaseModel):
    """Complete Section 4: Requirements Specification"""
    section_title: str = Field(default="4. REQUIREMENTS SPECIFICATION")
    functional_requirements: FunctionalRequirementsSection
    performance_requirements: PerformanceRequirementsSection
    interface_requirements: InterfaceRequirementsSection
    data_security: DataSecuritySection
    safety_risk_requirements: SafetyRiskRequirementsSection

