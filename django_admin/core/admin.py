import json
import os
from pathlib import Path

from django import forms
from django.contrib import admin, messages
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import transaction

from .models import (
    Address, AuditLog, Cart, CartItem, Category, Customer, EmailDeliveryLog,
    InventoryTransaction, Notification, Order, OrderItem, OrderStatusHistory,
    Payment, PaymentWebhookEvent, Product, ProductImage, StockReservation,
)
from .tasks import send_transactional_email
from redis import Redis


def publish_status_event(customer_id: int, order_number: str, order_status: str) -> None:
    try:
        Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.25, socket_timeout=0.25).publish(
            f"notifications:{customer_id}",
            json.dumps({"type": "order_status", "title": "Order updated", "message": f"{order_number} is now {order_status}"}),
        )
    except Exception:
        pass


class ProductImageForm(forms.ModelForm):
    upload = forms.ImageField(required=False, help_text="Optional local image upload")

    class Meta:
        model = ProductImage
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image_url"].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        upload = self.cleaned_data.get("upload")
        if upload:
            path = default_storage.save(f"products/{Path(upload.name).name}", upload)
            instance.image_url = f'{os.getenv("DJANGO_URL", "http://localhost:8001")}{default_storage.url(path)}'
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("image_url") and not cleaned.get("upload"):
            raise forms.ValidationError("Provide an image URL or upload a file.")
        return cleaned


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    form = ProductImageForm
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "stock", "low_stock", "is_active")
    list_filter = ("category", "is_active", "currency")
    search_fields = ("name", "sku", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]

    @admin.display(boolean=True, description="Low stock")
    def low_stock(self, obj):
        return obj.is_low_stock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "role", "is_active", "email_verified", "created_at")
    list_filter = ("role", "is_active", "email_verified")
    search_fields = ("name", "email", "auth0_id")
    readonly_fields = ("password_hash", "last_login_at", "created_at", "updated_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "product_sku", "unit_price", "quantity", "line_total")


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("provider", "amount", "status", "checkout_session_id", "payment_intent_id", "paid_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "total", "payment_status", "order_status", "created_at")
    list_filter = ("payment_status", "order_status", "created_at")
    search_fields = ("order_number", "customer__email")
    readonly_fields = ("order_number", "customer", "subtotal", "discount_total", "shipping_total", "tax_total", "total", "currency", "shipping_address", "created_at", "updated_at")
    inlines = [OrderItemInline, PaymentInline]

    def save_model(self, request, obj, form, change):
        previous = Order.objects.filter(pk=obj.pk).values_list("order_status", flat=True).first() if change else None
        super().save_model(request, obj, form, change)
        if previous and previous != obj.order_status:
            OrderStatusHistory.objects.create(order=obj, from_status=previous, to_status=obj.order_status)
            Notification.objects.create(
                customer=obj.customer,
                notification_type="order_status",
                title=f"Order {obj.order_status.replace('_', ' ')}",
                message=f"Your order {obj.order_number} is now {obj.order_status.replace('_', ' ')}.",
                metadata={"order_number": obj.order_number},
            )
            transaction.on_commit(lambda: send_transactional_email.delay(
                "order_status", obj.customer.email,
                {"name": obj.customer.name, "order_number": obj.order_number, "status": obj.order_status},
            ))
            transaction.on_commit(lambda: publish_status_event(obj.customer_id, obj.order_number, obj.order_status))
            messages.success(request, "Customer notification queued.")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "customer", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("customer__email", "title", "message")


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ("product", "transaction_type", "quantity_delta", "stock_after", "created_at")
    list_filter = ("transaction_type",)
    readonly_fields = ("created_at",)


admin.site.register(Address)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(ProductImage)
admin.site.register(Payment)
admin.site.register(StockReservation)
admin.site.register(OrderStatusHistory)
admin.site.register(PaymentWebhookEvent)
admin.site.register(EmailDeliveryLog)
admin.site.register(AuditLog)
admin.site.site_header = "Smart Commerce Administration"
admin.site.site_title = "Smart Commerce"
admin.site.index_title = "Operations"
