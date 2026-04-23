from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DevelopmentTool(StrictBaseModel):
    tool_name: str = Field(..., description="Name of the development tool")
    version: str = Field(..., description="Tool version")
    tool_qualification_level: Optional[str] = Field(
        default=None, description="DO-330 Tool Qualification Level (TQL-1 to TQL-5) if applicable"
    )
    usage: str = Field(..., description="Purpose or usage of this tool in the development process")


class AerospaceSoftwareDevelopmentPlanSchema(StrictBaseModel):
    section_number: str = Field(default="3", description="Section number")
    section_title: str = Field(default="Software Development Plan", description="Section title")
    development_environment: str = Field(..., description="Description of the development environment")
    development_tools: List[DevelopmentTool]
    standards_followed: List[str] = Field(..., description="Standards followed (DO-178C, MISRA, etc.)")
    lifecycle_model: str = Field(..., description="Software development lifecycle model used (waterfall, spiral, etc.)")
    coding_standards: List[str] = Field(..., description="Coding standards applied (MISRA C, CERT C, etc.)")
    configuration_management_tool: Optional[str] = Field(default=None, description="CM tool used (Git, ClearCase, etc.)")
