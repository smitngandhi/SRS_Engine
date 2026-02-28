from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoamingRequirement(StrictBaseModel):
    roaming_architecture: str = Field(..., description="Roaming architecture (Home-Routed, Local Breakout)")
    vplmn_interface: Optional[str] = Field(default=None, description="VPLMN interface specification (N32, IPX)")
    agreements_required: bool = Field(..., description="Whether roaming agreements with partner operators are required")


class LegacyInterworkingRequirement(StrictBaseModel):
    legacy_system: str = Field(..., description="Legacy network system (2G, 3G, 4G EPC)")
    interworking_function: str = Field(..., description="Interworking function used (N26, EPS-Fallback, etc.)")
    spec_reference: Optional[str] = Field(default=None, description="3GPP spec for this interworking")


class TelecomInteroperabilitySchema(StrictBaseModel):
    section_number: str = Field(default="9", description="Section number")
    section_title: str = Field(default="Interoperability Requirements", description="Section title")
    multi_vendor_interoperability: str = Field(..., description="Requirements for multi-vendor interoperability")
    roaming_requirements: Optional[RoamingRequirement] = Field(default=None)
    legacy_interworking: Optional[List[LegacyInterworkingRequirement]] = Field(default=None)
    conformance_test_bodies: Optional[List[str]] = Field(
        default=None, description="Conformance testing bodies (GCT, PTCRB, GCF)"
    )
    ota_testing_required: bool = Field(..., description="Whether OTA (Over The Air) testing is required")
