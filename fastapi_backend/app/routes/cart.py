from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemResponse, CartItemUpdate, CartResponse
from app.services.events import publish_user_event
from app.utils.auth import get_current_user


router = APIRouter(prefix="/cart", tags=["Cart"])


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def serialize_cart(db: Session, cart: Cart) -> CartResponse:
    rows = (
        db.query(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .filter(CartItem.cart_id == cart.id)
        .all()
    )
    items = []
    subtotal = Decimal("0.00")
    item_count = 0
    currency = "INR"
    for item, product in rows:
        image = db.query(ProductImage).filter(ProductImage.product_id == product.id, ProductImage.is_primary.is_(True)).first()
        line_total = Decimal(product.price) * item.quantity
        subtotal += line_total
        item_count += item.quantity
        currency = product.currency
        items.append(CartItemResponse(
            id=item.id, product_id=product.id, name=product.name, sku=product.sku,
            image_url=image.image_url if image else None, unit_price=product.price,
            quantity=item.quantity, line_total=line_total, available_stock=product.stock,
        ))
    return CartResponse(id=cart.id, items=items, item_count=item_count, subtotal=subtotal, currency=currency)


@router.get("", response_model=CartResponse)
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_cart(db, get_or_create_cart(db, user.id))


@router.post("/items", response_model=CartResponse, status_code=201)
def add_item(payload: CartItemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product or not product.is_active or product.deleted_at:
        raise HTTPException(status_code=404, detail="Product not found")
    cart = get_or_create_cart(db, user.id)
    item = db.query(CartItem).filter(CartItem.cart_id == cart.id, CartItem.product_id == product.id).first()
    requested = payload.quantity + (item.quantity if item else 0)
    if requested > product.stock:
        raise HTTPException(status_code=409, detail=f"Only {product.stock} item(s) available")
    if item:
        item.quantity = requested
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=payload.quantity))
    db.commit()
    publish_user_event(user.id, {"type": "cart_updated"})
    return serialize_cart(db, cart)


@router.patch("/items/{item_id}", response_model=CartResponse)
def update_item(item_id: int, payload: CartItemUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart = get_or_create_cart(db, user.id)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    product = db.get(Product, item.product_id)
    if payload.quantity > product.stock:
        raise HTTPException(status_code=409, detail=f"Only {product.stock} item(s) available")
    item.quantity = payload.quantity
    db.commit()
    publish_user_event(user.id, {"type": "cart_updated"})
    return serialize_cart(db, cart)


@router.delete("/items/{item_id}", status_code=204)
def remove_item(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart = get_or_create_cart(db, user.id)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    publish_user_event(user.id, {"type": "cart_updated"})
    return Response(status_code=204)
