from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PartitionDefinition(StrictBaseModel):
    partition_name: str = Field(..., description="Name of the software partition")
    dal_level: str = Field(..., description="DAL level assigned to this partition")
    memory_constraints: Optional[str] = Field(default=None, description="Memory budget for this partition")
    timing_constraints: Optional[str] = Field(default=None, description="Timing/scheduling constraints")


class InterPartitionCommunication(StrictBaseModel):
    source_partition: str = Field(..., description="Source partition")
    destination_partition: str = Field(..., description="Destination partition")
    mechanism: str = Field(..., description="Communication mechanism (shared memory, message passing, ARINC 653)")
    data_description: str = Field(..., description="Data exchanged between partitions")


class AerospaceSoftwareArchitectureSchema(StrictBaseModel):
    section_number: str = Field(default="8", description="Section number")
    section_title: str = Field(default="Software Architecture", description="Section title")
    architecture_description: str = Field(..., description="Overall software architecture description")
    partitions: List[PartitionDefinition]
    partitioning_strategy: str = Field(..., description="Rationale for partitioning approach (spatial, temporal)")
    inter_partition_communications: List[InterPartitionCommunication]
    rtos_used: Optional[str] = Field(default=None, description="Real-time operating system used")
    architecture_diagram_reference: Optional[str] = Field(
        default=None, description="Reference to architecture diagram document"
    )
