from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TelecomIntroductionSchema(StrictBaseModel):
    section_number: str = Field(default="1", description="Section number")
    section_title: str = Field(default="Introduction & Network Context", description="Section title")
    network_generation: Literal["2G", "3G", "4G", "5G", "5G-SA", "5G-NSA", "Multi-Generation"] = Field(
        ..., description="Network generation this software supports"
    )
    three_gpp_release: str = Field(..., description="3GPP release compliance (e.g. Release 15, 16, 17, 18)")
    network_element_type: Literal["RAN", "Core", "IMS", "Transport", "OSS/BSS", "VAS"] = Field(
        ..., description="Type of network element this software implements"
    )
    deployment_scenario: Literal["Public Network", "Non-Public Network", "Private 5G", "Shared Network"] = Field(
        ..., description="Network deployment scenario"
    )
    document_purpose: str = Field(..., description="Purpose and scope of this SRS")
    intended_audience: List[str] = Field(..., description="Intended audience")
