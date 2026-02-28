from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CourseManagementFeature(StrictBaseModel):
    feature_name: str = Field(..., description="Feature name (e.g. syllabus builder, module sequencing)")
    description: str = Field(..., description="Description of the feature")
    required: bool = Field(..., description="Whether this feature is mandatory")


class EducationLMSRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="3", description="Section number")
    section_title: str = Field(default="Learning Management System Requirements", description="Section title")
    course_creation_features: List[CourseManagementFeature]
    enrollment_types: List[str] = Field(..., description="Enrollment types (self-enroll, instructor-enroll, bulk import)")
    completion_tracking: bool = Field(..., description="Whether course completion tracking is required")
    prerequisite_support: Optional[bool] = Field(default=None, description="Whether course prerequisites are enforced")
    certificate_generation: Optional[bool] = Field(default=None, description="Whether certificates are auto-generated on completion")
    max_concurrent_users: Optional[int] = Field(default=None, description="Maximum concurrent user sessions supported")
    progress_reporting_features: List[str] = Field(..., description="Progress reporting features for instructors and admins")
