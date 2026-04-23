from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EducationContentManagementSchema(StrictBaseModel):
    section_number: str = Field(default="4", description="Section number")
    section_title: str = Field(default="Content Management & Delivery", description="Section title")
    supported_content_types: List[str] = Field(
        ..., description="Supported content types (video, audio, PDF, SCORM, H5P, xAPI)"
    )
    offline_access_supported: bool = Field(..., description="Whether offline content access is supported")
    scorm_version: Optional[str] = Field(default=None, description="SCORM version supported (SCORM 1.2, SCORM 2004)")
    xapi_supported: Optional[bool] = Field(default=None, description="Whether xAPI (Tin Can API) is supported")
    content_versioning: bool = Field(..., description="Whether content versioning is supported")
    supported_languages: List[str] = Field(..., description="Languages supported for content delivery (ISO 639-1 codes)")
    max_video_resolution: Optional[str] = Field(default=None, description="Maximum supported video resolution (e.g. 4K)")
    adaptive_bitrate: Optional[bool] = Field(default=None, description="Whether adaptive bitrate video streaming is required")
