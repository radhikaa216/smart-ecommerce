from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from redis import Redis
import json

from .models import EmailDeliveryLog, Notification, Order, StockReservation


def publish_event(customer_id: int, payload: dict) -> None:
    try:
        Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.25, socket_timeout=0.25).publish(
            f"notifications:{customer_id}", json.dumps(payload)
        )
    except Exception:
        pass


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_transactional_email(self, template_name: str, recipient: str, context: dict):
    log = EmailDeliveryLog.objects.create(
        recipient=recipient,
        template_name=template_name,
        status="queued",
        order=Order.objects.filter(order_number=context.get("order_number")).first(),
    )
    try:
        subject_map = {
            "order_confirmation": f"Order {context.get('order_number')} confirmed",
            "payment_failed": f"Payment issue for {context.get('order_number')}",
            "order_status": f"Order {context.get('order_number')} update",
        }
        subject = subject_map.get(template_name, "Smart Ecommerce notification")
        text = render_to_string("emails/notification.txt", {**context, "template_name": template_name})
        html = render_to_string("emails/notification.html", {**context, "template_name": template_name})
        message = EmailMultiAlternatives(subject, text, to=[recipient])
        message.attach_alternative(html, "text/html")
        message.send()
        log.status = "sent"
        log.save(update_fields=["status", "updated_at"])
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)[:1000]
        log.save(update_fields=["status", "error_message", "updated_at"])
        raise


@shared_task
def release_expired_stock():
    released = 0
    reservation_ids = list(StockReservation.objects.filter(status="active", expires_at__lte=timezone.now()).values_list("id", flat=True))
    for reservation_id in reservation_ids:
        with transaction.atomic():
            reservation = StockReservation.objects.select_for_update().select_related("product", "order", "order__customer").get(pk=reservation_id)
            if reservation.status != "active" or reservation.expires_at > timezone.now():
                continue
            product = type(reservation.product).objects.select_for_update().get(pk=reservation.product_id)
            product.stock += reservation.quantity
            product.save(update_fields=["stock", "updated_at"])
            reservation.status = "expired"
            reservation.save(update_fields=["status", "updated_at"])
            order = reservation.order
            if not order.reservations.filter(status="active").exclude(pk=reservation.pk).exists():
                order.order_status = "cancelled"
                order.payment_status = "failed"
                order.save(update_fields=["order_status", "payment_status", "updated_at"])
                Notification.objects.create(
                    customer=order.customer,
                    notification_type="payment_failed",
                    title="Checkout expired",
                    message=f"The payment window for {order.order_number} expired.",
                    metadata={"order_number": order.order_number},
                )
                transaction.on_commit(lambda: publish_event(
                    order.customer_id,
                    {"type": "payment_failed", "title": "Checkout expired", "message": f"The payment window for {order.order_number} expired."},
                ))
            released += 1
    return released
