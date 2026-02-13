from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class SystemDependency(StrictBaseModel):
    """External system or component dependency"""
    dependency_name: str = Field(..., description="Name of external system/component")
    dependency_type: str = Field(..., description="Hardware, Software, Network, Service")
    criticality: str = Field(..., description="Critical, Important, Optional")
    interface_method: str = Field(..., description="How systems communicate")


class ProductPerspectiveSection(StrictBaseModel):
    """
    Render as: PARAGRAPH + BULLETS
    Shows system context
    """
    title: str = Field(default="3.1 Product Perspective")
    system_context: str = Field(..., description="Overall system architecture narrative")
    dependencies: List[SystemDependency] = Field(..., description="External dependencies")
    boundary_description: str = Field(..., description="What is inside vs outside software boundary")
    
    # RENDER NOTE: Context and boundary as paragraphs, dependencies as bulleted list


class SystemFunction(StrictBaseModel):
    """High-level system function"""
    function_id: str = Field(..., description="Unique function identifier (SF-001)")
    function_name: str = Field(..., description="Short function name")
    description: str = Field(..., description="What the function does")
    user_benefit: str = Field(..., description="Clinical or operational benefit")
    safety_relevance: str = Field(..., description="Impact on patient safety")


class SystemFunctionsSection(StrictBaseModel):
    """
    Render as: TABLE
    Core functional overview
    """
    title: str = Field(default="3.2 System Functions")
    overview: str = Field(..., description="High-level functional overview paragraph")
    functions: List[SystemFunction] = Field(..., description="Detailed function list")
    
    # TABLE HEADERS: Function ID | Name | Description | User Benefit | Safety Relevance


class OperationalConstraint(StrictBaseModel):
    """System constraint or limitation"""
    constraint_type: str = Field(..., description="Performance, Regulatory, Technical, etc.")
    description: str = Field(..., description="Nature of the constraint")
    impact: str = Field(..., description="How this affects system design")
    mitigation: Optional[str] = Field(None, description="How constraint is managed")


class OperationalEnvironmentSection(StrictBaseModel):
    """
    Render as: MIXED (Paragraph + Table)
    Critical for deployment and risk assessment
    """
    title: str = Field(default="3.3 Operational Environment & Constraints")
    environment_description: str = Field(..., description="Where the software operates")
    hardware_requirements: List[str] = Field(..., description="Required hardware specifications")
    network_requirements: List[str] = Field(..., description="Network connectivity needs")
    operating_systems: List[str] = Field(..., description="Supported OS platforms")
    constraints: List[OperationalConstraint] = Field(..., description="Operational limitations")
    
    # RENDER NOTE: Description as paragraph, requirements as bullets, constraints as table


class SystemOverviewSection(StrictBaseModel):
    """Complete Section 3: System Overview & Description"""
    section_title: str = Field(default="3. SYSTEM OVERVIEW & DESCRIPTION")
    product_perspective: ProductPerspectiveSection
    system_functions: SystemFunctionsSection
    operational_environment: OperationalEnvironmentSection
