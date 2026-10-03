import math
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage
from app.schemas.catalog import CategoryResponse, ProductPage, ProductResponse


router = APIRouter(tags=["Catalog"])


def serialize_product(product: Product, category: Category, db: Session) -> ProductResponse:
    image = (
        db.query(ProductImage)
        .filter(ProductImage.product_id == product.id)
        .order_by(desc(ProductImage.is_primary), asc(ProductImage.sort_order))
        .first()
    )
    image_url = image.image_url if image else None
    if image_url and image_url.startswith("/"):
        image_url = f"{get_settings().django_url}{image_url}"
    return ProductResponse(
        id=product.id,
        category_id=product.category_id,
        category_name=category.name,
        name=product.name,
        slug=product.slug,
        sku=product.sku,
        description=product.description,
        price=Decimal(product.price),
        currency=product.currency,
        stock=product.stock,
        image_url=image_url,
        sales_count=product.sales_count,
    )


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active.is_(True)).order_by(Category.name).all()


@router.get("/products", response_model=ProductPage)
def list_products(
    q: str | None = None,
    category: str | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    in_stock: bool | None = None,
    sort: str = Query(default="newest", pattern="^(newest|price_asc|price_desc|popularity)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Product, Category)
        .join(Category, Product.category_id == Category.id)
        .filter(Product.is_active.is_(True), Product.deleted_at.is_(None), Category.is_active.is_(True))
    )
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(Product.name.ilike(term), Product.description.ilike(term), Product.sku.ilike(term)))
    if category:
        query = query.filter(Category.slug == category)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if in_stock is True:
        query = query.filter(Product.stock > 0)
    ordering = {
        "newest": desc(Product.created_at),
        "price_asc": asc(Product.price),
        "price_desc": desc(Product.price),
        "popularity": desc(Product.sales_count),
    }[sort]
    total = query.count()
    rows = query.order_by(ordering).offset((page - 1) * page_size).limit(page_size).all()
    return ProductPage(
        items=[serialize_product(product, cat, db) for product, cat in rows],
        page=page,
        page_size=page_size,
        total=total,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/products/{slug}", response_model=ProductResponse)
def get_product(slug: str, db: Session = Depends(get_db)):
    row = (
        db.query(Product, Category)
        .join(Category, Product.category_id == Category.id)
        .filter(Product.slug == slug, Product.is_active.is_(True), Product.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(row[0], row[1], db)
