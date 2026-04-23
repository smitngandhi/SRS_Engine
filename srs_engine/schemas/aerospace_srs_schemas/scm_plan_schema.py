from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfigurationItem(StrictBaseModel):
    item_name: str = Field(..., description="Name of the configuration item")
    item_type: str = Field(..., description="Type (source code, test case, requirements document, tool)")
    identifier: str = Field(..., description="Unique identifier for this configuration item")


class ChangeControlProcess(StrictBaseModel):
    change_request_process: str = Field(..., description="How change requests are submitted and tracked")
    approval_authority: str = Field(..., description="Who approves changes to controlled items")
    impact_analysis_required: bool = Field(
        default=True, description="Whether impact analysis is required before change approval"
    )


class AerospaceSCMPlanSchema(StrictBaseModel):
    section_number: str = Field(default="5", description="Section number")
    section_title: str = Field(default="Software Configuration Management Plan", description="Section title")
    configuration_items: List[ConfigurationItem]
    baseline_control: str = Field(..., description="Description of baseline control process")
    change_control: ChangeControlProcess
    version_control_system: str = Field(..., description="Version control system used")
    problem_reporting_tool: Optional[str] = Field(default=None, description="Problem/defect reporting tool used")
