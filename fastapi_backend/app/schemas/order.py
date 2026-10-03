from decimal import Decimal

from pydantic import BaseModel, Field


class AddressInput(BaseModel):
    recipient_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=6, max_length=32)
    line1: str = Field(min_length=3, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=3, max_length=20)
    country_code: str = Field(default="IN", min_length=2, max_length=2)


class CheckoutRequest(BaseModel):
    shipping_address: AddressInput
    customer_note: str | None = Field(default=None, max_length=1000)


class CheckoutResponse(BaseModel):
    order_number: str
    checkout_session_id: str
    checkout_url: str


class OrderItemResponse(BaseModel):
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderResponse(BaseModel):
    order_number: str
    subtotal: Decimal
    shipping_total: Decimal
    tax_total: Decimal
    total: Decimal
    currency: str
    payment_status: str
    order_status: str
    shipping_address: dict
    created_at: str
    items: list[OrderItemResponse]
