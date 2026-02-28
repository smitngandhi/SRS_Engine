from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NetworkSliceRequirement(StrictBaseModel):
    slice_type: str = Field(..., description="Network slice type (eMBB, URLLC, mMTC)")
    s_nssai: str = Field(..., description="Single Network Slice Selection Assistance Information value")
    isolation_requirements: str = Field(..., description="Slice isolation requirements")
    sla_parameters: Optional[List[str]] = Field(default=None, description="SLA parameters for this slice")


class TelecomNetworkManagementSchema(StrictBaseModel):
    section_number: str = Field(default="6", description="Section number")
    section_title: str = Field(default="Network Management Requirements", description="Section title")
    configuration_management: str = Field(..., description="Configuration management approach and tools")
    fault_management: str = Field(..., description="Fault management approach (alarm categories, escalation)")
    performance_management: str = Field(..., description="KPI/KQI definitions and collection approach")
    network_slicing: Optional[List[NetworkSliceRequirement]] = Field(
        default=None, description="Network slicing management requirements (5G)"
    )
    son_capabilities: Optional[List[str]] = Field(
        default=None, description="Self-Organizing Network capabilities (SON) required"
    )
    management_interface: Optional[str] = Field(
        default=None, description="Management interface standard (NETCONF/YANG, SNMP, REST)"
    )
