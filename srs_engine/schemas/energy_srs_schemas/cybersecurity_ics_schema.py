from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NetworkSegmentationRequirement(StrictBaseModel):
    zone_name: str = Field(..., description="Security zone name (Corporate, Control, Field, DMZ)")
    trust_level: str = Field(..., description="Trust level of this zone")
    allowed_communications: List[str] = Field(..., description="Allowed inter-zone communications")
    firewall_rules_required: bool = Field(..., description="Whether firewall rules are required between zones")


class ICSAccessControl(StrictBaseModel):
    system_component: str = Field(..., description="ICS component (HMI, Historian, RTU, IED)")
    authentication_method: str = Field(..., description="Authentication method required")
    role_based_access: bool = Field(..., description="Whether role-based access control (RBAC) is required")
    remote_access_policy: Optional[str] = Field(default=None, description="Remote access policy for this component")


class EnergyICSCybersecuritySchema(StrictBaseModel):
    section_number: str = Field(default="6", description="Section number")
    section_title: str = Field(default="Cybersecurity Requirements (ICS)", description="Section title")
    nerc_cip_cybersecurity_applicable: bool = Field(
        ..., description="Whether NERC CIP cybersecurity standards apply"
    )
    network_segmentation: List[NetworkSegmentationRequirement]
    access_control: List[ICSAccessControl]
    patch_management_policy: Optional[str] = Field(
        default=None, description="Patch management policy for ICS components"
    )
    security_event_monitoring: bool = Field(
        ..., description="Whether security event monitoring (SIEM) is required"
    )
    incident_response_plan_reference: Optional[str] = Field(
        default=None, description="Reference to ICS cybersecurity incident response plan"
    )
