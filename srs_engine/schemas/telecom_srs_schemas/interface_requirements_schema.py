from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExternalInterface(StrictBaseModel):
    interface_name: str = Field(..., description="Interface name (e.g. N1, N2, N3, N4, Xn, F1, E1)")
    connected_nf: str = Field(..., description="Network function or node connected via this interface")
    protocol: str = Field(..., description="Protocol used (SCTP, HTTP/2, GTP, NGAP, PFCP)")
    spec_reference: str = Field(..., description="3GPP specification reference for this interface")
    direction: Literal["Bidirectional", "Upstream", "Downstream"] = Field(..., description="Interface data direction")


class APISpec(StrictBaseModel):
    api_name: str = Field(..., description="API name or OpenAPI spec name")
    api_style: Literal["REST", "SOAP", "gRPC", "WebSocket"] = Field(..., description="API communication style")
    authentication_mechanism: Optional[str] = Field(default=None, description="Authentication mechanism (OAuth 2.0, mTLS)")
    spec_document: Optional[str] = Field(default=None, description="Reference to API specification document")


class TelecomInterfaceRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="5", description="Section number")
    section_title: str = Field(default="Interface Requirements", description="Section title")
    external_interfaces: List[ExternalInterface]
    api_specifications: Optional[List[APISpec]] = Field(default=None)
    inter_node_protocols: Optional[List[str]] = Field(
        default=None, description="Inter-node communication protocols used"
    )
