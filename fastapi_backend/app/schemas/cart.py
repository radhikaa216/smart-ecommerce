from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=99)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=99)


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    name: str
    sku: str
    image_url: str | None
    unit_price: Decimal
    quantity: int
    line_total: Decimal
    available_stock: int


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    item_count: int
    subtotal: Decimal
    currency: str
