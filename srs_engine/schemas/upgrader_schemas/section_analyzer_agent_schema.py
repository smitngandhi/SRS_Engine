from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SectionScoreOutput(StrictBaseModel):
    completeness: float = Field(..., ge=0, le=10)
    clarity: float      = Field(..., ge=0, le=10)
    ieee_compliance: float = Field(..., ge=0, le=10)
    testability: float  = Field(..., ge=0, le=10)
    consistency: float  = Field(..., ge=0, le=10)


class SectionAnalysisOutput(StrictBaseModel):
    scores: SectionScoreOutput
    flags: list[str] = Field(default_factory=list)
    needs_upgrade: bool
    brief_summary: str