from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionItem(StrictBaseModel):
    question_id: str
    question: str
    dimension: Literal[
        "completeness", "clarity", "ieee_compliance",
        "testability", "consistency"
    ]


class QuestionEngineOutput(StrictBaseModel):
    questions: list[QuestionItem]