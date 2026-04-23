from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SystemFunctionalRequirement(StrictBaseModel):
    req_id: str = Field(..., description="System functional requirement ID (e.g. SYS-FR-001)")
    description: str = Field(..., description="Functional requirement description")
    linked_safety_goal: Optional[str] = Field(default=None, description="Linked safety goal ID if safety-relevant")


class SystemNonFunctionalRequirement(StrictBaseModel):
    req_id: str = Field(..., description="System non-functional requirement ID")
    category: str = Field(..., description="Category (performance, reliability, maintainability, etc.)")
    description: str = Field(..., description="Non-functional requirement description")
    measurement_criteria: Optional[str] = Field(default=None, description="How this requirement will be measured")


class HardwareSoftwareInterfaceRequirement(StrictBaseModel):
    hsi_id: str = Field(..., description="HSI requirement ID")
    hardware_element: str = Field(..., description="Hardware element this interface connects to")
    interface_description: str = Field(..., description="Description of the hardware-software interface")
    signal_voltage: Optional[str] = Field(default=None, description="Signal voltage levels if applicable")
    communication_protocol: Optional[str] = Field(default=None, description="Communication protocol (CAN, LIN, FlexRay, Ethernet)")


class AutomotiveSystemRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="3", description="Section number")
    section_title: str = Field(default="System Requirements", description="Section title")
    functional_requirements: List[SystemFunctionalRequirement]
    non_functional_requirements: List[SystemNonFunctionalRequirement]
    hardware_software_interface_requirements: List[HardwareSoftwareInterfaceRequirement]
    autosar_compliance: bool = Field(..., description="Whether AUTOSAR compliance is required")
    autosar_version: Optional[str] = Field(default=None, description="AUTOSAR version targeted (Classic, Adaptive)")
