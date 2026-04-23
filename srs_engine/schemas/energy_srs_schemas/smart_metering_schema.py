from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EnergySmartMeteringSchema(StrictBaseModel):
    section_number: str = Field(default="4", description="Section number")
    section_title: str = Field(default="Smart Metering Requirements (AMI)", description="Section title")
    meter_data_collection_interval_minutes: int = Field(
        ..., description="How often meter data is collected (in minutes)"
    )
    communication_protocols: List[str] = Field(
        ..., description="AMI communication protocols (RF Mesh, PLC, Cellular)"
    )
    demand_response_supported: bool = Field(..., description="Whether demand response programs are supported")
    outage_detection: bool = Field(..., description="Whether last-gasp outage detection is supported")
    tamper_detection: bool = Field(..., description="Whether meter tamper detection is supported")
    tamper_detection_methods: Optional[List[str]] = Field(
        default=None, description="Tamper detection methods (magnetic tamper, reverse energy, etc.)"
    )
    prepayment_supported: Optional[bool] = Field(default=None, description="Whether prepayment metering is supported")
    mdm_integration: Optional[str] = Field(default=None, description="Meter Data Management system integration details")
