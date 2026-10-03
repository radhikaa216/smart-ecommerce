from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.notification import Notification
from app.models.product import Product
from app.models.stock_reservation import StockReservation
from app.models.user import User
from app.schemas.order import OrderItemResponse, OrderResponse
from app.utils.auth import get_current_user
from app.services.events import publish_user_event, queue_email


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


@router.get("/{order_number}", response_model=OrderResponse)
def get_order(order_number: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_number == order_number, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_order(db, order)


@router.post("/{order_number}/cancel", response_model=OrderResponse)
def cancel_order(order_number: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_number == order_number, Order.user_id == user.id).with_for_update().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.order_status not in {"pending_payment", "confirmed"}:
        raise HTTPException(status_code=409, detail="This order can no longer be cancelled")
    if order.payment_status == "paid":
        raise HTTPException(status_code=409, detail="Paid orders require an administrator refund")
    reservations = db.query(StockReservation).filter(StockReservation.order_id == order.id, StockReservation.status == "active").all()
    for reservation in reservations:
        product = db.query(Product).filter(Product.id == reservation.product_id).with_for_update().one()
        product.stock += reservation.quantity
        reservation.status = "released"
    order.order_status = "cancelled"
    notification = Notification(
        user_id=user.id, notification_type="order_cancelled", title="Order cancelled",
        message=f"Order {order.order_number} has been cancelled.", metadata_json={"order_number": order.order_number},
    )
    db.add(notification)
    db.commit()
    publish_user_event(user.id, {"type": "order_cancelled", "title": notification.title, "message": notification.message})
    queue_email("order_status", user.email, {"name": user.name, "order_number": order.order_number, "status": "cancelled"})
    return serialize_order(db, order)
