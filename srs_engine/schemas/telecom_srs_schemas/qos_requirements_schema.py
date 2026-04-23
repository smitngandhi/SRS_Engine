from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QoSFlowRequirement(StrictBaseModel):
    qfi: int = Field(..., description="QoS Flow Identifier (0-63)")
    five_qi: Optional[int] = Field(default=None, description="5G QoS Indicator value (1-86)")
    gbr_type: bool = Field(..., description="Whether this is a GBR (Guaranteed Bit Rate) flow")
    max_data_rate_mbps: Optional[float] = Field(default=None, description="Maximum data rate in Mbps")
    guaranteed_data_rate_mbps: Optional[float] = Field(default=None, description="Guaranteed data rate in Mbps for GBR flows")
    packet_delay_budget_ms: Optional[int] = Field(default=None, description="Packet Delay Budget in ms")
    packet_error_rate: Optional[str] = Field(default=None, description="Packet Error Rate target (e.g. 10^-6)")


class TelecomQoSRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="7", description="Section number")
    section_title: str = Field(default="Quality of Service (QoS) Requirements", description="Section title")
    qos_flows: List[QoSFlowRequirement]
    traffic_prioritization_policy: str = Field(..., description="Traffic prioritization policy description")
    end_to_end_latency_ms: Optional[int] = Field(default=None, description="End-to-end latency requirement in ms")
    throughput_target_mbps: Optional[float] = Field(default=None, description="System throughput target in Mbps")
    reliability_target: Optional[str] = Field(default=None, description="Reliability target (e.g. 99.999%)")
