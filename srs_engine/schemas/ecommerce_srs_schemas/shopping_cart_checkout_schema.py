from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentGateway(StrictBaseModel):
    gateway_name: str = Field(..., description="Payment gateway name (Stripe, Braintree, PayPal, etc.)")
    supported_methods: List[str] = Field(..., description="Payment methods supported by this gateway")
    pci_compliant: bool = Field(..., description="Whether this gateway is PCI DSS compliant")


class EcommerceShoppingCartCheckoutSchema(StrictBaseModel):
    section_number: str = Field(default="4", description="Section number")
    section_title: str = Field(default="Shopping Cart & Checkout", description="Section title")
    guest_checkout_supported: bool = Field(..., description="Whether guest checkout without account is supported")
    cart_persistence_days: Optional[int] = Field(default=None, description="How many days cart is persisted for logged-in users")
    payment_gateways: List[PaymentGateway]
    supported_currencies: List[str] = Field(..., description="Supported currencies (ISO 4217 codes)")
    tax_calculation_engine: str = Field(..., description="Tax calculation approach (integrated engine, third-party like Avalara)")
    shipping_calculation: str = Field(..., description="Shipping calculation approach (flat rate, real-time carrier rates)")
    buy_now_pay_later_supported: Optional[bool] = Field(default=None, description="Whether BNPL options are supported")
