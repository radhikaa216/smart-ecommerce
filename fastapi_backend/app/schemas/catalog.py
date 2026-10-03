from decimal import Decimal

from pydantic import BaseModel


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None


class ProductResponse(BaseModel):
    id: int
    category_id: int
    category_name: str
    name: str
    slug: str
    sku: str
    description: str | None
    price: Decimal
    currency: str
    stock: int
    image_url: str | None
    sales_count: int


class ProductPage(BaseModel):
    items: list[ProductResponse]
    page: int
    page_size: int
    total: int
    pages: int
