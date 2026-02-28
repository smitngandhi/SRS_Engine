from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EducationIntroductionSchema(StrictBaseModel):
    section_number: str = Field(default="1", description="Section number")
    section_title: str = Field(default="Introduction & Educational Context", description="Section title")
    institution_type: Literal["K-12", "Higher Education", "Vocational", "Corporate Training", "EdTech Platform"] = Field(
        ..., description="Type of educational institution or platform"
    )
    learning_model: Literal["Online", "Blended", "In-Person", "Self-Paced", "Instructor-Led"] = Field(
        ..., description="Learning delivery model"
    )
    target_age_group: str = Field(..., description="Target age group (e.g. 6-12, 13-17, 18+, Adults)")
    user_profiles: List[str] = Field(..., description="User profiles (student, instructor, admin, parent)")
    applicable_standards: List[str] = Field(..., description="Applicable standards (FERPA, COPPA, GDPR, WCAG 2.1, etc.)")
    document_purpose: str = Field(..., description="Purpose and scope of this SRS")
