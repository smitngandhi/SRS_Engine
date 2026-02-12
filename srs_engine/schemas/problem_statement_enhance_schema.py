from typing import List, Optional
from pydantic import BaseModel, ConfigDict , Field

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class EnhanceProblemStatementInput(StrictBaseModel):
    project_name: str
    problem_statement: str


class EnhancedProblemStatementSection(StrictBaseModel):
    enhanced_problem_statement: str  # 50-1000 characters
