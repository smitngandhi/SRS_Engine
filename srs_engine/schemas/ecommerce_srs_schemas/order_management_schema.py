from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrderStatus(StrictBaseModel):
    status_name: str = Field(..., description="Order status (Pending, Confirmed, Processing, Shipped, Delivered, Cancelled)")
    description: str = Field(..., description="Description of this order state")
    customer_notification: bool = Field(..., description="Whether customer is notified when order enters this state")


class EcommerceOrderManagementSchema(StrictBaseModel):
    section_number: str = Field(default="5", description="Section number")
    section_title: str = Field(default="Order Management", description="Section title")
    order_statuses: List[OrderStatus]
    order_tracking_supported: bool = Field(..., description="Whether real-time order tracking is provided to customers")
    return_window_days: Optional[int] = Field(default=None, description="Return window in days")
    refund_types_supported: List[str] = Field(..., description="Supported refund types (full, partial, store credit)")
    inventory_sync_real_time: bool = Field(..., description="Whether inventory is synced in real-time on order placement")
    split_fulfillment_supported: Optional[bool] = Field(default=None, description="Whether split shipment from multiple warehouses is supported")
