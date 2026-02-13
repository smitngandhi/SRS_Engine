from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# SECTION 2: SOFTWARE SAFETY CLASSIFICATION
# ============================================================================

class SafetyClassificationRationale(StrictBaseModel):
    """Detailed reasoning for safety class assignment"""
    factor: str = Field(..., description="Factor considered (injury severity, probability, etc.)")
    analysis: str = Field(..., description="How this factor was evaluated")
    conclusion: str = Field(..., description="Impact on classification")


class SoftwareSafetyClassificationSection(StrictBaseModel):
    """
    Render as: MIXED (Highlighted box + Table)
    Critical determination per IEC 62304
    """
    section_title: str = Field(default="2. SOFTWARE SAFETY CLASSIFICATION")
    safety_class: Literal["A", "B", "C"] = Field(..., description="IEC 62304 Software Safety Class")
    classification_summary: str = Field(..., description="Executive summary of classification")
    rationale_details: List[SafetyClassificationRationale] = Field(..., description="Detailed reasoning")
    injury_scenarios: List[str] = Field(..., description="Potential injury scenarios considered")
    risk_control_measures: str = Field(..., description="How risks are controlled in design")