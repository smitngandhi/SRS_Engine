from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PCIDSSRequirement(StrictBaseModel):
    dss_level: Literal["Level 1", "Level 2", "Level 3", "Level 4"] = Field(
        ..., description="PCI DSS merchant or service provider level"
    )
    card_data_scope: str = Field(..., description="Description of card data in scope (CHD environment)")
    tokenization_used: bool = Field(..., description="Whether tokenization is used for card data")
    encryption_standard: str = Field(..., description="Encryption standard for card data (AES-256, TLS 1.3)")


class GDPRRequirement(StrictBaseModel):
    data_subjects: List[str] = Field(..., description="Categories of EU data subjects")
    lawful_basis: str = Field(..., description="Lawful basis for processing (consent, contract, legitimate interest)")
    dpo_required: bool = Field(..., description="Whether a Data Protection Officer is required")
    dpia_required: bool = Field(..., description="Whether a Data Protection Impact Assessment is required")


class CCPARequirement(StrictBaseModel):
    opt_out_mechanism: str = Field(..., description="Mechanism for California residents to opt out of data sale")
    data_deletion_supported: bool = Field(..., description="Whether right to deletion is supported")
    privacy_notice_url: Optional[str] = Field(default=None, description="URL to the California privacy notice")


class AuthenticationRequirement(StrictBaseModel):
    mfa_required: bool = Field(..., description="Whether multi-factor authentication is required")
    mfa_methods: Optional[List[str]] = Field(default=None, description="Supported MFA methods (TOTP, SMS, biometric)")
    session_timeout_seconds: Optional[int] = Field(default=None, description="Session timeout in seconds")


class FinanceSecurityDataProtectionSchema(StrictBaseModel):
    section_number: str = Field(default="3", description="Section number")
    section_title: str = Field(default="Security & Data Protection", description="Section title")
    pci_dss: PCIDSSRequirement
    gdpr: Optional[GDPRRequirement] = Field(default=None, description="GDPR requirements if EU data is in scope")
    ccpa: Optional[CCPARequirement] = Field(default=None, description="CCPA requirements if California data is in scope")
    encryption_at_rest: str = Field(..., description="Encryption standard for data at rest")
    encryption_in_transit: str = Field(..., description="Encryption standard for data in transit")
    authentication: AuthenticationRequirement
