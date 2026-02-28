from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreditRiskControl(StrictBaseModel):
    assessment_method: str = Field(..., description="Credit risk assessment method (score model, bureau pull, etc.)")
    credit_bureau_integrations: Optional[List[str]] = Field(
        default=None, description="Credit bureaus integrated (Equifax, Experian, TransUnion)"
    )
    risk_threshold: Optional[str] = Field(default=None, description="Credit score or risk threshold for decisions")


class OperationalRiskControl(StrictBaseModel):
    control_id: str = Field(..., description="Unique control ID")
    description: str = Field(..., description="Description of the operational risk control")
    control_type: str = Field(..., description="Type of control (preventive, detective, corrective)")


class CybersecurityRiskAssessment(StrictBaseModel):
    ffiec_guidelines_followed: bool = Field(..., description="Whether FFIEC cybersecurity guidelines are followed")
    vulnerability_scanning_frequency: Optional[str] = Field(
        default=None, description="Frequency of vulnerability scanning"
    )
    penetration_testing_required: bool = Field(..., description="Whether pen testing is required")


class ThirdPartyRisk(StrictBaseModel):
    vendor_name: str = Field(..., description="Third-party vendor or service provider name")
    service_provided: str = Field(..., description="Service provided by this vendor")
    due_diligence_required: bool = Field(..., description="Whether due diligence review is required")
    contract_requirements: Optional[List[str]] = Field(
        default=None, description="Contractual risk requirements (SLA, security addendum)"
    )


class FinanceRiskManagementSchema(StrictBaseModel):
    section_number: str = Field(default="6", description="Section number")
    section_title: str = Field(default="Risk Management Requirements", description="Section title")
    credit_risk: Optional[CreditRiskControl] = Field(default=None)
    operational_risk_controls: List[OperationalRiskControl]
    cybersecurity_risk: CybersecurityRiskAssessment
    third_party_risks: Optional[List[ThirdPartyRisk]] = Field(default=None)
    market_risk_description: Optional[str] = Field(default=None, description="Market risk controls description if applicable")
