from typing import List
from pydantic import BaseModel, ConfigDict, Field

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class SYSTEM_CONSTRAINTS_Section(StrictBaseModel):
    """
    Schema for system constraints generation.
    
    Constraints are technical or business restrictions that limit design options.
    Examples:
    - "System must operate with less than 2GB RAM"
    - "Must be compatible with IE11"
    - "Must work offline"
    - "Limited to open-source libraries"
    """
    system_constraints: List[str] = Field(
        ...,
        min_items=3,
        max_items=8,
        description="List of 3-8 technical or business constraints.",
        examples=[[
            "Must be deployed on-premise",
            "System must operate with less than 2GB RAM",
            "Must comply with GDPR regulations",
            "Limited to open-source libraries"
        ]]
    )
