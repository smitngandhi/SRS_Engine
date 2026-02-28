from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EnergyGridManagementSchema(StrictBaseModel):
    section_number: str = Field(default="5", description="Section number")
    section_title: str = Field(default="Grid Management Requirements", description="Section title")
    load_forecasting: bool = Field(..., description="Whether load forecasting capability is required")
    load_forecasting_horizon_hours: Optional[int] = Field(
        default=None, description="Load forecasting horizon in hours"
    )
    distribution_automation: bool = Field(..., description="Whether distribution automation (DA) is required")
    volt_var_optimization: Optional[bool] = Field(default=None, description="Whether Volt/VAR optimization is required")
    flisr_required: bool = Field(
        ..., description="Whether Fault Location, Isolation, and Service Restoration (FLISR) is required"
    )
    der_management: Optional[bool] = Field(
        default=None, description="Whether Distributed Energy Resource (DER) management is required"
    )
    outage_management_integration: Optional[str] = Field(
        default=None, description="Outage Management System (OMS) integration requirements"
    )
