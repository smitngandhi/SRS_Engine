from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KPI(StrictBaseModel):
    metric_name: str = Field(..., description="KPI or metric name (CVR, AOV, CAC, LTV, etc.)")
    description: str = Field(..., description="Metric description and calculation method")
    real_time: bool = Field(..., description="Whether this metric is available in real-time")


class EcommerceAnalyticsReportingSchema(StrictBaseModel):
    section_number: str = Field(default="8", description="Section number")
    section_title: str = Field(default="Analytics & Reporting", description="Section title")
    kpis: List[KPI]
    customer_behavior_tracking: bool = Field(..., description="Whether customer behavior (clickstream) is tracked")
    conversion_funnel_analysis: bool = Field(..., description="Whether conversion funnel analysis is provided")
    ab_testing_supported: bool = Field(..., description="Whether A/B testing capabilities are required")
    analytics_platform: Optional[str] = Field(default=None, description="Analytics platform used (GA4, Mixpanel, Amplitude)")
    data_retention_days: Optional[int] = Field(default=None, description="Analytics data retention period in days")
