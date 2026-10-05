from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.schemas.order import OrderItemResponse, OrderResponse
from app.utils.auth import get_current_user


router = APIRouter(prefix="/orders", tags=["Orders"])


def serialize_order(db: Session, order: Order) -> OrderResponse:
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    return OrderResponse(
        order_number=order.order_number,
        subtotal=order.subtotal,
        shipping_total=order.shipping_total,
        tax_total=order.tax_total,
        total=order.total,
        currency=order.currency,
        payment_status=order.payment_status,
        order_status=order.order_status,
        shipping_address=order.shipping_address,
        created_at=order.created_at.isoformat(),
        items=[OrderItemResponse(
            product_name=item.product_name, product_sku=item.product_sku,
            quantity=item.quantity, unit_price=item.unit_price, line_total=item.line_total,
        ) for item in items],
    )


@router.get("", response_model=list[OrderResponse])
def list_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.user_id == user.id).order_by(desc(Order.created_at)).all()
    return [serialize_order(db, order) for order in orders]