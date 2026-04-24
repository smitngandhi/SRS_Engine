from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NetworkFunction(StrictBaseModel):
    nf_name: str = Field(..., description="Network function name (AMF, SMF, UPF, PCF, UDM, AUSF, etc.)")
    plane: Literal["User Plane", "Control Plane", "Management Plane"] = Field(
        ..., description="Plane this NF operates in"
    )
    description: str = Field(..., description="Description of this network function's responsibilities")
    served_interfaces: List[str] = Field(..., description="SBI or reference point interfaces served (e.g. N1, N2, Nsmf)")
    gpp_spec_reference: Optional[str] = Field(
        default=None, description="3GPP spec defining this NF (e.g. TS 23.502)"
    )


class SBAInterface(StrictBaseModel):
    interface_name: str = Field(..., description="Service-Based Architecture interface name (e.g. Namf)")
    producer_nf: str = Field(..., description="NF producing this service")
    consumer_nfs: List[str] = Field(..., description="NFs consuming this service")
    api_standard: Literal["HTTP/2", "REST", "SOAP"] = Field(..., description="API standard used")
    spec_reference: Optional[str] = Field(default=None, description="3GPP spec reference for this interface")


class TelecomNetworkFunctionsSchema(StrictBaseModel):
    section_number: str = Field(default="3", description="Section number")
    section_title: str = Field(default="Network Functions Requirements", description="Section title")
    network_functions: List[NetworkFunction]
    sba_interfaces: Optional[List[SBAInterface]] = Field(
        default=None, description="Service-Based Architecture interfaces (5G Core)"
    )
