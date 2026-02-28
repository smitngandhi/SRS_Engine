from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentProcessingSpec(StrictBaseModel):
    supported_payment_types: List[str] = Field(..., description="Supported payment types (credit, debit, ACH, wire)")
    transaction_limit: Optional[str] = Field(default=None, description="Per-transaction or daily limits")
    processing_latency_ms: Optional[int] = Field(default=None, description="Maximum allowed processing latency in ms")


class ACHWireCapability(StrictBaseModel):
    ach_supported: bool = Field(..., description="Whether ACH transfers are supported")
    wire_transfer_supported: bool = Field(..., description="Whether wire transfers are supported")
    same_day_ach: Optional[bool] = Field(default=None, description="Whether same-day ACH is supported")
    swift_supported: Optional[bool] = Field(default=None, description="Whether SWIFT international wires are supported")


class RealTimePayment(StrictBaseModel):
    rtp_network: Optional[str] = Field(default=None, description="Real-time payment network used (RTP, FedNow)")
    max_rtp_amount: Optional[str] = Field(default=None, description="Maximum amount for real-time payments")


class FraudDetection(StrictBaseModel):
    real_time_screening: bool = Field(..., description="Whether real-time fraud screening is applied")
    ml_model_used: Optional[bool] = Field(default=None, description="Whether an ML-based fraud model is used")
    rule_based_checks: List[str] = Field(..., description="List of rule-based fraud checks applied")
    chargeback_handling: Optional[str] = Field(default=None, description="Chargeback handling process")


class ReconciliationProcess(StrictBaseModel):
    reconciliation_frequency: Literal["Real-time", "Hourly", "Daily", "Weekly"] = Field(
        ..., description="How often reconciliation runs"
    )
    settlement_window: Optional[str] = Field(default=None, description="Settlement window (e.g. T+1, T+2)")
    discrepancy_handling: str = Field(..., description="Process for handling reconciliation discrepancies")


class FinanceTransactionProcessingSchema(StrictBaseModel):
    section_number: str = Field(default="4", description="Section number")
    section_title: str = Field(default="Transaction Processing Requirements", description="Section title")
    payment_processing: PaymentProcessingSpec
    ach_wire: ACHWireCapability
    real_time_payment: Optional[RealTimePayment] = Field(default=None)
    fraud_detection: FraudDetection
    reconciliation: ReconciliationProcess
