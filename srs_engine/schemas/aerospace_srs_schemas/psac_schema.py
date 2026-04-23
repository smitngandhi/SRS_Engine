from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StageOfInvolvement(StrictBaseModel):
    soi_number: Literal["SOI-1", "SOI-2", "SOI-3", "SOI-4"] = Field(
        ..., description="Stage of Involvement number (SOI-1=Planning, SOI-2=Development, SOI-3=V&V, SOI-4=Final)"
    )
    activities: List[str] = Field(..., description="Activities performed at this stage of involvement")
    authority_review_required: bool = Field(..., description="Whether certification authority review is required at this SOI")


class AerospacePSACSchema(StrictBaseModel):
    section_number: str = Field(default="2", description="Section number")
    section_title: str = Field(default="Plan for Software Aspects of Certification (PSAC)", description="Section title")
    software_development_approach: str = Field(..., description="Overall software development approach (iterative, waterfall, etc.)")
    certification_liaison_process: str = Field(..., description="Process for communicating with the certification authority")
    stages_of_involvement: List[StageOfInvolvement]
    alternative_methods: Optional[List[str]] = Field(
        default=None, description="Any alternative methods proposed to certification authority"
    )
