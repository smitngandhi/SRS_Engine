from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionType(StrictBaseModel):
    type_name: str = Field(..., description="Question type (MCQ, True/False, Short Answer, Essay, Fill-in-the-blank)")
    auto_graded: bool = Field(..., description="Whether this question type supports auto-grading")


class AntiCheatingMeasure(StrictBaseModel):
    measure_name: str = Field(..., description="Anti-cheating measure name")
    description: str = Field(..., description="Description of how this measure prevents cheating")
    requires_proctoring: bool = Field(..., description="Whether this measure requires a proctoring service")


class EducationAssessmentGradingSchema(StrictBaseModel):
    section_number: str = Field(default="5", description="Section number")
    section_title: str = Field(default="Assessment & Grading System", description="Section title")
    question_types: List[QuestionType]
    grading_scale: str = Field(..., description="Grading scale used (letter, percentage, pass/fail, points)")
    auto_grading_supported: bool = Field(..., description="Whether auto-grading is supported")
    rubric_based_grading: Optional[bool] = Field(default=None, description="Whether rubric-based grading is supported")
    anti_cheating_measures: List[AntiCheatingMeasure]
    time_limits_supported: bool = Field(..., description="Whether timed assessments are supported")
    attempt_limit: Optional[int] = Field(default=None, description="Maximum number of attempts allowed per assessment")
    grade_export_formats: List[str] = Field(..., description="Export formats for grades (CSV, LIS, SIS API)")
