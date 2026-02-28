from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WCAGRequirement(StrictBaseModel):
    principle: Literal["Perceivable", "Operable", "Understandable", "Robust"] = Field(
        ..., description="WCAG 2.1 accessibility principle"
    )
    success_criteria: List[str] = Field(..., description="Applicable WCAG success criteria (e.g. 1.1.1, 1.2.1)")
    conformance_level: Literal["A", "AA", "AAA"] = Field(..., description="Minimum required WCAG conformance level")


class EducationAccessibilitySchema(StrictBaseModel):
    section_number: str = Field(default="6", description="Section number")
    section_title: str = Field(default="Accessibility Requirements (WCAG/Section 508)", description="Section title")
    wcag_version: str = Field(default="2.1", description="WCAG version to comply with")
    minimum_conformance_level: Literal["A", "AA", "AAA"] = Field(
        ..., description="Minimum WCAG conformance level required"
    )
    section_508_applicable: bool = Field(..., description="Whether Section 508 compliance is required (US federal funding)")
    wcag_requirements: List[WCAGRequirement]
    screen_reader_compatible: bool = Field(..., description="Whether full screen reader compatibility is required")
    keyboard_navigation: bool = Field(..., description="Whether complete keyboard-only navigation is required")
    color_contrast_ratio_minimum: float = Field(
        ..., description="Minimum color contrast ratio (4.5:1 for WCAG AA normal text)"
    )
    closed_captioning_required: bool = Field(..., description="Whether closed captioning is required for all media")
    audio_descriptions_required: bool = Field(..., description="Whether audio descriptions for video content are required")
