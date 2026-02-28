from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ASPICEProcessArea(StrictBaseModel):
    process_id: Literal["SWE.1", "SWE.2", "SWE.3", "SWE.4", "SWE.5", "SWE.6"] = Field(
        ..., description="ASPICE software engineering process ID"
    )
    process_name: str = Field(..., description="Process name")
    target_capability_level: Literal["CL0", "CL1", "CL2", "CL3"] = Field(
        ..., description="Target ASPICE capability level for this process"
    )
    work_products: List[str] = Field(..., description="Work products produced by this process")
    responsible_role: Optional[str] = Field(default=None, description="Role responsible for this process area")


class AutomotiveASPICEProcessSchema(StrictBaseModel):
    section_number: str = Field(default="7", description="Section number")
    section_title: str = Field(default="ASPICE Process Requirements", description="Section title")
    target_aspice_level: Literal["CL1", "CL2", "CL3"] = Field(
        ..., description="Overall target ASPICE capability level"
    )
    process_areas: List[ASPICEProcessArea]
    assessment_planned: bool = Field(..., description="Whether a formal ASPICE assessment is planned")
    assessment_body: Optional[str] = Field(default=None, description="Assessment body if formal assessment is planned")
