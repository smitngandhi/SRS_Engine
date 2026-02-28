from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinanceIntroductionSchema(StrictBaseModel):
    section_number: str = Field(default="1", description="Section number")
    section_title: str = Field(default="Introduction & Scope", description="Section title")
    financial_service_type: Literal["Payments", "Lending", "Investment", "Banking", "Insurance", "Crypto"] = Field(
        ..., description="Type of financial service the software supports"
    )
    regulatory_jurisdiction: List[str] = Field(..., description="Regulatory jurisdictions (US, EU, APAC, etc.)")
    license_requirements: Optional[List[str]] = Field(
        default=None, description="License requirements e.g. MTL (Money Transmitter License), RIA, Broker-Dealer"
    )
    document_purpose: str = Field(..., description="Purpose and scope of this SRS document")
    intended_audience: List[str] = Field(..., description="Intended audience for this document")
