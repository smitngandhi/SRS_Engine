from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FraudPreventionRule(StrictBaseModel):
    rule_name: str = Field(..., description="Fraud rule name")
    description: str = Field(..., description="Description of what this rule detects")
    automated_action: str = Field(..., description="Automated action taken (block, flag, 3DS challenge)")


class EcommercePaymentProcessingSchema(StrictBaseModel):
    section_number: str = Field(default="6", description="Section number")
    section_title: str = Field(default="Payment Processing (PCI DSS)", description="Section title")
    pci_dss_level: Literal["Level 1", "Level 2", "Level 3", "Level 4"] = Field(
        ..., description="PCI DSS compliance level required"
    )
    cardholder_data_stored: bool = Field(..., description="Whether cardholder data is stored (affects scope)")
    tokenization_required: bool = Field(..., description="Whether payment tokenization is required")
    three_ds_required: bool = Field(..., description="Whether 3D Secure authentication is required")
    fraud_prevention_rules: List[FraudPreventionRule]
    chargeback_management: Optional[str] = Field(default=None, description="Chargeback management process")
