from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SystemIntegration(StrictBaseModel):
    system_name: str = Field(..., description="Name of integrated system (GIS, CIS, WMS, OMS, Billing)")
    integration_type: str = Field(..., description="Integration type (real-time, batch, event-driven)")
    protocol: str = Field(..., description="Integration protocol (REST API, SOAP, MQ, CIM XML)")
    data_exchanged: List[str] = Field(..., description="Data exchanged with this system")
    cim_based: Optional[bool] = Field(default=None, description="Whether integration uses IEC CIM (Common Information Model)")


class EnergyIntegrationRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="7", description="Section number")
    section_title: str = Field(default="Integration Requirements", description="Section title")
    system_integrations: List[SystemIntegration]
    iec_cim_version: Optional[str] = Field(default=None, description="IEC CIM version used for enterprise integration")
    esb_or_middleware: Optional[str] = Field(
        default=None, description="Enterprise Service Bus or middleware platform used"
    )
