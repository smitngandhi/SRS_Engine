from typing import List
from pydantic import BaseModel, ConfigDict, Field

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class KEY_ASSUMPTIONS_Section(StrictBaseModel):
    """
    Schema for key assumptions generation.
    
    Assumptions are facts considered to be true for the system to function correctly.
    Examples:
    - "Users have a stable internet connection"
    - "Third-party APIs remain unchanged"
    - "Incoming data follows the specified schema"
    """
    key_assumptions: List[str] = Field(
        ...,
        min_items=3,
        max_items=8,
        description="List of 3-8 key assumptions for the project.",
        examples=[[
            "Users have a stable internet connection",
            "Third-party payment gateway remains available",
            "Incoming CSV data follows the specified schema",
            "End-users are familiar with basic web interfaces"
        ]]
    )
