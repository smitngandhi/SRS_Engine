from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductPerspective(StrictBaseModel):
    system_context: str = Field(..., description="How the medical software fits into the larger system")
    parent_system: Optional[str] = Field(default=None, description="Name of the parent system or device")
    dependencies: Optional[List[str]] = Field(default=None, description="External systems this software depends on")


class SystemFunctions(StrictBaseModel):
    function_name: str = Field(..., description="Name of the big-picture function")
    function_description: str = Field(..., description="Description of what the function does (monitoring, reporting, control, etc.)")


class OperationalEnvironment(StrictBaseModel):
    hardware_requirements: List[str] = Field(..., description="Hardware the software runs on")
    network_requirements: Optional[List[str]] = Field(default=None, description="Network or connectivity constraints")
    regulatory_dependencies: Optional[List[str]] = Field(default=None, description="Regulatory compliance dependencies affecting environment")
    performance_limitations: Optional[List[str]] = Field(default=None, description="Known performance limitations of the environment")


class HealthcareSystemOverviewSchema(StrictBaseModel):
    section_number: str = Field(default="3", description="Section number")
    section_title: str = Field(default="System Overview & Description", description="Section title")
    product_perspective: ProductPerspective
    system_functions: List[SystemFunctions]
    operational_environment: OperationalEnvironment