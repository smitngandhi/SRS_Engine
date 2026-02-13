from typing import List, Optional
from pydantic import BaseModel, ConfigDict , Field

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CORE_FEATURES_Section(StrictBaseModel):
    """
    Schema for core features generation.
    
    Each feature should be:
    - Clear and actionable
    - Focused on a single functionality
    - Written in present tense (e.g., "User authentication", "Data visualization")
    - Brief but descriptive (5-10 words max per feature)
    
    Examples:
    - "User registration and authentication"
    - "Dashboard with real-time analytics"
    - "CSV/Excel data file upload"
    - "Predictive model training and evaluation"
    - "Automated email notifications"
    - "Role-based access control"
    - "Export reports in PDF format"
    """
    core_features: List[str] = Field(
        ...,
        min_items=4,
        max_items=12,
        description=(
            "List of 4-12 core features for the project. "
            "Each feature should be concise (5-10 words), actionable, and focused on a single functionality. "
            "Features should cover the essential capabilities needed to solve the problem statement. "
            "Include features for: user interaction, data handling, core business logic, "
            "reporting/visualization, and system management."
        ),
        examples=[
            [
                "User registration and authentication",
                "Dashboard with real-time analytics", 
                "CSV data file upload and validation",
                "Predictive model training",
                "Churn risk scoring and visualization",
                "Automated alert notifications",
                "Historical data analysis",
                "Export reports in PDF format"
            ]
        ]
    )


