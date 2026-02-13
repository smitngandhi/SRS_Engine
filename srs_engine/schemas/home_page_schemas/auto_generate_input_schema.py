from pydantic import BaseModel, Field, validator
from typing import List, Optional



class AutoGenerateInput(BaseModel):
    project_name: str = Field(..., description="Name of the project")
    problem_statement: str = Field(..., description="Problem this system is intended to solve")
    section_type: str = Field(..., description="Type of section to generate (e.g., 'core_features', 'primary_user_flow')")
    
    @validator('project_name', 'problem_statement', 'section_type')
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()