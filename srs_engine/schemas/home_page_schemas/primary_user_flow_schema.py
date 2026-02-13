from typing import List, Optional
from pydantic import BaseModel, ConfigDict , Field

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PRIMARY_USER_FLOW_Section(StrictBaseModel):
    """
    Schema for primary user flow generation.
    
    The flow should describe the typical user journey through the system:
    - Start with user entry point (login, landing page, etc.)
    - Include key actions in logical sequence
    - Cover data input, processing, and output
    - End with the final outcome or exit point
    - Be written in clear, action-oriented language
    - Use simple present tense or imperative mood
    
    Format: Multi-step narrative or numbered list
    
    Example 1 (Narrative):
    "User logs into the system using credentials, navigates to the dashboard to view recent churn predictions. 
    User uploads a new customer dataset in CSV format, which is automatically validated. 
    The system processes the data and generates churn risk scores. 
    User reviews the prediction results in an interactive visualization, 
    filters high-risk customers, and exports a detailed report for the management team."
    
    Example 2 (Numbered):
    "1. User logs in with email and password
    2. User navigates to the data upload page
    3. User selects and uploads customer data file (CSV/Excel)
    4. System validates and processes the data
    5. User views churn prediction results on dashboard
    6. User filters results by risk level
    7. User exports report or sets up automated alerts
    8. User logs out"
    """
    primary_user_flow: str = Field(
        ...,
        min_length=100,
        max_length=800,
        description=(
            "A clear, step-by-step description of how a primary user interacts with the system "
            "to accomplish their main goal. Should be 100-800 characters long, covering the complete "
            "user journey from entry to exit. Include: login/access, main actions, data operations, "
            "viewing results, and any export/notification steps. Use clear, action-oriented language."
        ),
        examples=[
            (
                "User logs into the system, navigates to the data upload section, and uploads a CSV file "
                "containing customer information. The system validates the data and displays a confirmation. "
                "User then navigates to the prediction dashboard where the ML model analyzes the data and "
                "generates churn risk scores. User reviews the visualization showing high-risk customers, "
                "applies filters to segment the results, and exports a detailed report in PDF format for "
                "the management team. User can also set up automated email alerts for new high-risk cases."
            )
        ]
    )