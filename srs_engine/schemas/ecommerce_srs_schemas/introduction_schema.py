from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EcommerceIntroductionSchema(StrictBaseModel):
    section_number: str = Field(default="1", description="Section number")
    section_title: str = Field(default="Introduction & Business Model", description="Section title")
    platform_type: Literal["B2C", "B2B", "C2C", "Marketplace", "D2C", "Subscription"] = Field(
        ..., description="E-commerce business model type"
    )
    target_markets: List[str] = Field(..., description="Target markets and geographic regions")
    applicable_standards: List[str] = Field(..., description="Applicable standards (PCI DSS, GDPR, CCPA, etc.)")
    document_purpose: str = Field(..., description="Purpose and scope of this SRS")
    intended_audience: List[str] = Field(..., description="Intended audience for this document")
