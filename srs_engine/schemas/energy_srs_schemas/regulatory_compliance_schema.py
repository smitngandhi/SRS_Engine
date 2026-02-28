from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NERCCIPStandard(StrictBaseModel):
    standard_id: str = Field(..., description="NERC CIP standard ID (e.g. CIP-002-5.1a)")
    title: str = Field(..., description="NERC CIP standard title")
    applicable_bcs: List[str] = Field(..., description="Applicable BES Cyber Systems")
    requirements: List[str] = Field(..., description="Key requirements from this standard")


class EnergyRegulatoryComplianceSchema(StrictBaseModel):
    section_number: str = Field(default="2", description="Section number")
    section_title: str = Field(default="Regulatory Compliance (NERC CIP)", description="Section title")
    nerc_cip_standards: List[NERCCIPStandard]
    ferc_requirements: Optional[List[str]] = Field(default=None, description="Applicable FERC regulatory requirements")
    environmental_compliance: Optional[List[str]] = Field(
        default=None, description="Environmental compliance requirements"
    )
    iec_61850_compliance: bool = Field(..., description="Whether IEC 61850 compliance is required")
    ieee_1547_compliance: Optional[bool] = Field(
        default=None, description="Whether IEEE 1547 (DER interconnection) compliance is required"
    )
