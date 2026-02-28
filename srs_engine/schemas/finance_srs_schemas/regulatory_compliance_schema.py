from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AMLControl(StrictBaseModel):
    control_id: str = Field(..., description="Unique AML control ID")
    description: str = Field(..., description="Description of the AML control measure")
    monitoring_rule: Optional[str] = Field(default=None, description="Monitoring rule or threshold used")


class KYCRequirement(StrictBaseModel):
    req_id: str = Field(..., description="Unique KYC requirement ID")
    verification_type: str = Field(..., description="Type of identity verification (document, biometric, database)")
    data_collected: List[str] = Field(..., description="Data collected during KYC verification")
    retention_period: Optional[str] = Field(default=None, description="How long KYC data is retained")


class CTFMeasure(StrictBaseModel):
    measure_id: str = Field(..., description="Unique CTF measure ID")
    description: str = Field(..., description="Counter-Terrorism Financing measure description")


class SanctionsScreening(StrictBaseModel):
    ofac_screening_enabled: bool = Field(..., description="Whether OFAC screening is implemented")
    screening_lists: List[str] = Field(..., description="Sanctions lists screened against (OFAC SDN, EU Consolidated, etc.)")
    screening_frequency: str = Field(..., description="When screening occurs (real-time, batch, on-boarding)")


class BSACompliance(StrictBaseModel):
    sar_filing_required: bool = Field(..., description="Whether Suspicious Activity Reports are required")
    ctr_filing_required: bool = Field(..., description="Whether Currency Transaction Reports are required")
    recordkeeping_requirements: List[str] = Field(..., description="BSA recordkeeping obligations")


class FinanceRegulatoryComplianceSchema(StrictBaseModel):
    section_number: str = Field(default="2", description="Section number")
    section_title: str = Field(default="Regulatory Compliance Requirements", description="Section title")
    aml_controls: List[AMLControl]
    kyc_requirements: List[KYCRequirement]
    ctf_measures: List[CTFMeasure]
    sanctions_screening: SanctionsScreening
    bsa_compliance: BSACompliance
    fair_lending_requirements: Optional[List[str]] = Field(
        default=None, description="Fair lending requirements (TILA, FCRA) if applicable"
    )
