from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class ArchitectureComponent(StrictBaseModel):
    """Software component/module description"""
    component_id: str = Field(..., description="Unique component ID (COMP-001)")
    component_name: str = Field(..., description="Component name")
    purpose: str = Field(..., description="What this component does")
    safety_classification: str = Field(..., description="Safety class of this component")
    key_functions: List[str] = Field(..., description="Main functions performed")


class ArchitectureOverviewSection(StrictBaseModel):
    """
    Render as: PARAGRAPH + DIAGRAM + BULLETS
    High-level architecture
    """
    title: str = Field(default="5.1 Architecture Overview")
    architecture_description: str = Field(..., description="Overall architecture approach (layered, microservices, etc.)")
    design_principles: List[str] = Field(..., description="Key design principles followed")
    components: List[ArchitectureComponent] = Field(..., description="Major software components")
    architecture_diagram_reference: Optional[str] = Field(None, description="Reference to architecture diagram")
    
    # RENDER NOTE: Description as paragraph, principles as bullets, components as nested bullets


class ComponentInterface(StrictBaseModel):
    """Interface between components - TABLE ROW"""
    interface_id: str = Field(..., description="Unique interface ID (CI-001)")
    source_component: str = Field(..., description="Component sending data")
    target_component: str = Field(..., description="Component receiving data")
    interface_type: str = Field(..., description="API, Message Queue, Shared Memory, etc.")
    data_exchanged: str = Field(..., description="What data flows through this interface")
    safety_implications: str = Field(..., description="Safety considerations for this interface")


class ComponentInterfacesSection(StrictBaseModel):
    """
    Render as: TABLE
    Critical for hazard analysis
    """
    title: str = Field(default="5.2 Interfaces Between Components")
    overview: str = Field(..., description="How components communicate")
    interfaces: List[ComponentInterface] = Field(..., description="All internal interfaces")
    
    # TABLE HEADERS: Interface ID | Source | Target | Type | Data | Safety Implications


class RiskSegregationSection(StrictBaseModel):
    """
    Render as: PARAGRAPH + BULLETS
    Shows risk containment strategy
    """
    title: str = Field(default="5.3 Segregation & Risk Control")
    segregation_strategy: str = Field(..., description="How safety-critical parts are isolated")
    safety_critical_components: List[str] = Field(..., description="Components classified as safety-critical")
    isolation_mechanisms: List[str] = Field(..., description="Technical isolation methods used")
    failure_containment: str = Field(..., description="How failures are prevented from propagating")
    
    # RENDER NOTE: Strategy as paragraph, components and mechanisms as bullets


class SoftwareArchitectureSection(StrictBaseModel):
    """Complete Section 5: Software Architecture Description"""
    section_title: str = Field(default="5. SOFTWARE ARCHITECTURE DESCRIPTION")
    note: str = Field(default="This section may reference separate Software Architecture Document (SAD)")
    architecture_overview: ArchitectureOverviewSection
    component_interfaces: ComponentInterfacesSection
    risk_segregation: RiskSegregationSection
