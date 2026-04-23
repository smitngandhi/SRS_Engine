from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SoftwareComponent(StrictBaseModel):
    swc_name: str = Field(..., description="AUTOSAR Software Component name")
    swc_type: Literal[
        "Application", "Composition", "Service", "ECU Abstraction", "Complex Driver", "Sensor Actuator"
    ] = Field(..., description="AUTOSAR SWC type")
    asil: Literal["QM", "A", "B", "C", "D"] = Field(..., description="ASIL level of this SWC")
    provided_ports: Optional[List[str]] = Field(default=None, description="Provided interface ports")
    required_ports: Optional[List[str]] = Field(default=None, description="Required interface ports")
    linked_requirements: Optional[List[str]] = Field(default=None, description="Requirement IDs this SWC implements")


class BSWModule(StrictBaseModel):
    module_name: str = Field(..., description="Basic Software module name (OS, Com, Dcm, Dem, etc.)")
    category: str = Field(..., description="BSW category (Microcontroller Abstraction, ECU Abstraction, Services)")
    configuration_reference: Optional[str] = Field(default=None, description="Reference to BSW configuration document")


class CommunicationMatrixEntry(StrictBaseModel):
    signal_name: str = Field(..., description="Signal or PDU name")
    sender_swc: str = Field(..., description="Sender SWC")
    receiver_swc: str = Field(..., description="Receiver SWC")
    bus_type: str = Field(..., description="Communication bus (CAN, LIN, FlexRay, Ethernet)")
    message_id: Optional[str] = Field(default=None, description="CAN message ID or equivalent identifier")
    cycle_time_ms: Optional[int] = Field(default=None, description="Signal transmission cycle time in ms")


class AutomotiveSoftwareArchitectureDesignSchema(StrictBaseModel):
    section_number: str = Field(default="5", description="Section number")
    section_title: str = Field(default="Software Architecture Design (AUTOSAR)", description="Section title")
    software_components: List[SoftwareComponent]
    bsw_modules: List[BSWModule]
    rte_description: str = Field(..., description="Runtime Environment (RTE) description and configuration approach")
    communication_matrix: List[CommunicationMatrixEntry]
    architecture_diagram_reference: Optional[str] = Field(
        default=None, description="Reference to architecture diagram"
    )
