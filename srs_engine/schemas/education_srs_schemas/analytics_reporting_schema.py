from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AtRiskIndicator(StrictBaseModel):
    indicator_name: str = Field(..., description="At-risk indicator (e.g. missed assignments, low grade trend, low login frequency)")
    threshold: str = Field(..., description="Threshold that triggers at-risk flag")
    alert_recipient: str = Field(..., description="Who receives the alert (instructor, advisor, admin)")


class EducationAnalyticsReportingSchema(StrictBaseModel):
    section_number: str = Field(default="8", description="Section number")
    section_title: str = Field(default="Analytics & Reporting", description="Section title")
    learning_analytics_dashboard: bool = Field(..., description="Whether a learning analytics dashboard is required")
    at_risk_indicators: List[AtRiskIndicator]
    instructor_performance_reports: bool = Field(..., description="Whether instructor performance reports are generated")
    institutional_compliance_reporting: bool = Field(
        ..., description="Whether institutional compliance reports (IPEDS, accreditation) are generated"
    )
    predictive_analytics: Optional[bool] = Field(default=None, description="Whether predictive analytics (outcome forecasting) is required")
    export_formats: List[str] = Field(..., description="Report export formats (PDF, CSV, Excel, API)")
