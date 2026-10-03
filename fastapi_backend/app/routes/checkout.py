import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.notification import Notification
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.stock_reservation import StockReservation
from app.models.user import User
from app.models.webhook_event import PaymentWebhookEvent
from app.schemas.order import CheckoutRequest, CheckoutResponse
from app.services.events import publish_user_event, queue_email
from app.utils.auth import get_current_user


router = APIRouter(prefix="/checkout", tags=["Checkout"])


def _order_number() -> str:
    return f"ORD-{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


def _notify(db: Session, order: Order, title: str, message: str, notification_type: str) -> Notification:
    notification = Notification(
        user_id=order.user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        metadata_json={"order_number": order.order_number},
    )
    db.add(notification)
    db.flush()
    return notification


def _release_reservations(db: Session, order: Order, reservation_status: str = "released") -> None:
    reservations = db.query(StockReservation).filter(
        StockReservation.order_id == order.id,
        StockReservation.status == "active",
    ).with_for_update().all()
    for reservation in reservations:
        product = db.query(Product).filter(Product.id == reservation.product_id).with_for_update().one()
        product.stock += reservation.quantity
        reservation.status = reservation_status


def _mark_paid(db: Session, order: Order, payment_intent_id: str | None = None) -> Notification | None:
    if order.payment_status == "paid":
        return None
    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    payment.status = "succeeded"
    payment.payment_intent_id = payment_intent_id or payment.payment_intent_id
    payment.transaction_id = payment.payment_intent_id
    payment.paid_at = datetime.utcnow()
    order.payment_status = "paid"
    order.order_status = "confirmed"
    order.placed_at = datetime.utcnow()
    reservations = db.query(StockReservation).filter(StockReservation.order_id == order.id).all()
    for reservation in reservations:
        if reservation.status == "active":
            reservation.status = "consumed"
            product = db.get(Product, reservation.product_id)
            product.sales_count += reservation.quantity
    return _notify(
        db, order, "Order confirmed", f"Payment received for {order.order_number}.", "order_confirmed"
    )


@router.post("/create-session", response_model=CheckoutResponse, status_code=201)
def create_checkout_session(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all() if cart else []
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    order = Order(
        order_number=_order_number(), user_id=user.id, subtotal=0, shipping_total=0,
        tax_total=0, discount_total=0, total=0, currency=settings.stripe_currency.upper(),
        shipping_address=payload.shipping_address.model_dump(), customer_note=payload.customer_note,
    )
    db.add(order)
    db.flush()
    stripe_items = []
    subtotal = Decimal("0.00")
    expires_at = datetime.utcnow() + timedelta(minutes=30)

    try:
        for cart_item in cart_items:
            product = db.query(Product).filter(Product.id == cart_item.product_id).with_for_update().one()
            if not product.is_active or product.deleted_at or product.stock < cart_item.quantity:
                raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}")
            product.stock -= cart_item.quantity
            line_total = Decimal(product.price) * cart_item.quantity
            subtotal += line_total
            image = db.query(ProductImage).filter(
                ProductImage.product_id == product.id, ProductImage.is_primary.is_(True)
            ).first()
            db.add(OrderItem(
                order_id=order.id, product_id=product.id, product_name=product.name,
                product_sku=product.sku, product_image_url=image.image_url if image else None,
                quantity=cart_item.quantity, unit_price=product.price, line_total=line_total,
            ))
            db.add(StockReservation(
                order_id=order.id, product_id=product.id, quantity=cart_item.quantity,
                status="active", expires_at=expires_at,
            ))
            stripe_items.append({
                "price_data": {
                    "currency": settings.stripe_currency,
                    "product_data": {"name": product.name},
                    "unit_amount": int(Decimal(product.price) * 100),
                },
                "quantity": cart_item.quantity,
            })

        order.subtotal = subtotal
        order.total = subtotal
        payment = Payment(order_id=order.id, amount=order.total, currency=order.currency, status="pending")
        db.add(payment)
        db.flush()

        if settings.stripe_demo_mode:
            session_id = f"cs_demo_{uuid.uuid4().hex}"
            checkout_url = f"{settings.frontend_url}/checkout/success?demo=1&order={order.order_number}"
        else:
            if not settings.stripe_secret_key:
                raise HTTPException(status_code=503, detail="Stripe test credentials are not configured")
            stripe.api_key = settings.stripe_secret_key
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=stripe_items,
                customer_email=user.email,
                success_url=f"{settings.frontend_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.frontend_url}/cart?checkout=cancelled",
                metadata={"order_id": str(order.id), "order_number": order.order_number},
                expires_at=int(expires_at.timestamp()),
            )
            session_id = session.id
            checkout_url = session.url
        payment.checkout_session_id = session_id
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail="Unable to initialize Stripe Checkout") from exc

    publish_user_event(user.id, {"type": "cart_updated"})
    return CheckoutResponse(
        order_number=order.order_number,
        checkout_session_id=session_id,
        checkout_url=checkout_url,
    )


@router.post("/demo-complete/{order_number}")
def complete_demo_checkout(
    order_number: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not get_settings().stripe_demo_mode:
        raise HTTPException(status_code=404, detail="Demo checkout is disabled")
    # Serialize repeated browser callbacks so only one request can transition
    # the order to paid and enqueue its confirmation email.
    order = db.query(Order).filter(
        Order.order_number == order_number,
        Order.user_id == user.id,
    ).with_for_update().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    notification = _mark_paid(db, order, f"pi_demo_{uuid.uuid4().hex}")
    db.commit()
    if notification:
        publish_user_event(user.id, {"id": notification.id, "title": notification.title, "message": notification.message})
        queue_email("order_confirmation", user.email, {"name": user.name, "order_number": order.order_number, "total": str(order.total)})
    return {"order_number": order.order_number, "payment_status": order.payment_status}


@router.post("/stripe/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.stripe_webhook_secret or not stripe_signature:
        raise HTTPException(status_code=400, detail="Stripe webhook is not configured")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature") from exc

    event_id = event["id"]
    existing = db.query(PaymentWebhookEvent).filter(PaymentWebhookEvent.provider_event_id == event_id).first()
    if existing:
        return {"received": True, "duplicate": True}
    stored_event = PaymentWebhookEvent(
        provider_event_id=event_id,
        event_type=event["type"],
        payload=json.loads(payload.decode("utf-8")),
    )
    db.add(stored_event)
    db.flush()

    session = event["data"]["object"]
    session_id = session.get("id")
    payment = db.query(Payment).filter(
        Payment.checkout_session_id == session_id
    ).with_for_update().first()
    if not payment:
        stored_event.processing_status = "ignored"
        db.commit()
        return {"received": True, "ignored": True}
    order = db.query(Order).filter(Order.id == payment.order_id).with_for_update().one()
    notification = None
    if event["type"] == "checkout.session.completed":
        notification = _mark_paid(db, order, session.get("payment_intent"))
    elif event["type"] in {"checkout.session.expired", "checkout.session.async_payment_failed"}:
        payment.status = "cancelled"
        order.payment_status = "failed"
        order.order_status = "cancelled"
        _release_reservations(db, order, "expired")
        notification = _notify(db, order, "Checkout expired", f"Checkout for {order.order_number} expired.", "payment_failed")
    else:
        stored_event.processing_status = "ignored"
    if stored_event.processing_status != "ignored":
        stored_event.processing_status = "processed"
        stored_event.processed_at = datetime.utcnow()
    db.commit()

    if notification:
        user = db.get(User, order.user_id)
        publish_user_event(order.user_id, {"id": notification.id, "title": notification.title, "message": notification.message})
        template = "order_confirmation" if order.payment_status == "paid" else "payment_failed"
        queue_email(template, user.email, {"name": user.name, "order_number": order.order_number, "total": str(order.total)})
    return {"received": True}
