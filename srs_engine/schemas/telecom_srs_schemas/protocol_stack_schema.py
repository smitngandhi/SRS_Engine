from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProtocolLayerRequirement(StrictBaseModel):
    layer_name: str = Field(..., description="Protocol layer name (PHY, MAC, RLC, PDCP, SDAP, RRC, NAS)")
    spec_reference: str = Field(..., description="3GPP specification for this layer (e.g. TS 38.321 for MAC)")
    key_requirements: List[str] = Field(..., description="Key requirements for this layer")
    performance_targets: Optional[List[str]] = Field(default=None, description="Performance targets (throughput, latency, error rate)")


class TelecomProtocolStackSchema(StrictBaseModel):
    section_number: str = Field(default="4", description="Section number")
    section_title: str = Field(default="Protocol Stack Requirements", description="Section title")
    physical_layer: ProtocolLayerRequirement
    mac_layer: ProtocolLayerRequirement
    rlc_layer: ProtocolLayerRequirement
    pdcp_layer: ProtocolLayerRequirement
    rrc_layer: ProtocolLayerRequirement
    nas_layer: ProtocolLayerRequirement
    additional_layers: Optional[List[ProtocolLayerRequirement]] = Field(
        default=None, description="Additional protocol layers (SDAP, GTP-U, etc.)"
    )
