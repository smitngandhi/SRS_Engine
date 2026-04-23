from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MonitoringRequirement(StrictBaseModel):
    parameter_name: str = Field(..., description="Parameter being monitored (voltage, current, frequency, pressure)")
    scan_rate_ms: int = Field(..., description="Monitoring scan rate in milliseconds")
    accuracy_percent: Optional[float] = Field(default=None, description="Required measurement accuracy as percentage")
    protocol: str = Field(..., description="Communication protocol (DNP3, Modbus, IEC 61850, ICCP)")


class AlarmRequirement(StrictBaseModel):
    alarm_id: str = Field(..., description="Alarm identifier")
    alarm_type: Literal["Priority 1", "Priority 2", "Priority 3", "Advisory"] = Field(
        ..., description="Alarm priority classification"
    )
    trigger_condition: str = Field(..., description="Condition that triggers this alarm")
    response_time_seconds: int = Field(..., description="Maximum time to display alarm after trigger")
    acknowledgment_required: bool = Field(..., description="Whether operator acknowledgment is required")


class EnergySCADAControlSchema(StrictBaseModel):
    section_number: str = Field(default="3", description="Section number")
    section_title: str = Field(default="SCADA & Control Requirements", description="Section title")
    real_time_monitoring: List[MonitoringRequirement]
    control_actions: List[str] = Field(..., description="Control actions the system must support (switch, breaker, valve)")
    alarm_management: List[AlarmRequirement]
    historian_data_requirements: Optional[str] = Field(
        default=None, description="Data historian requirements (retention period, resolution)"
    )
    system_availability_percent: float = Field(..., description="Required system availability percentage (e.g. 99.99)")
