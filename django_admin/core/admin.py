import json
import os
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.core.files.storage import default_storage
from django.db import transaction
from passlib.context import CryptContext
from redis import Redis

from .models import (
    Category, Customer, Notification, Order, OrderItem, OrderStatusHistory,
    Payment, Product, ProductImage,
)
from .tasks import send_transactional_email


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
    """Images are managed from their product, not from a separate menu."""

    model = ProductImage
    form = ProductImageForm
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "stock", "low_stock", "is_active")
    list_filter = ("category", "is_active", "currency")
    search_fields = ("name", "sku", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("category",)
    list_per_page = 25
    inlines = [ProductImageInline]
    fieldsets = (
        ("Product information", {"fields": ("name", "slug", "sku", "category", "description")}),
        ("Price and inventory", {"fields": ("price", "currency", "stock", "low_stock_threshold", "sales_count")}),
        ("Visibility", {"fields": ("is_active", "deleted_at")}),
    )

    @admin.display(boolean=True, description="Low stock")
    def low_stock(self, obj):
        return obj.is_low_stock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_per_page = 25


class UnifiedUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(required=False, widget=forms.PasswordInput)
    password2 = forms.CharField(required=False, widget=forms.PasswordInput)

    class Meta:
        model = Customer
        fields = ("email", "name", "role", "is_active", "is_staff", "is_superuser", "email_verified")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("The two password fields do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
            user.password_hash = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class UnifiedUserChangeForm(forms.ModelForm):
    local_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Optional. Sets a new local password for both Django Admin and FastAPI login.",
    )

    class Meta:
        model = Customer
        fields = ("email", "name", "role", "is_active", "is_staff", "is_superuser", "email_verified", "avatar_url")

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("local_password")
        if password:
            user.set_password(password)
            user.password_hash = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)
        if commit:
            user.save()
        return user


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "role", "is_staff", "is_active", "email_verified", "created_at")
    list_filter = ("role", "is_staff", "is_active", "email_verified")
    search_fields = ("name", "email", "auth0_id")
    list_per_page = 25
    readonly_fields = ("auth0_id", "password_hash", "last_login", "last_login_at", "created_at", "updated_at")

    def get_form(self, request, obj=None, **kwargs):
        kwargs["form"] = UnifiedUserCreationForm if obj is None else UnifiedUserChangeForm
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                ("Profile", {"fields": ("name", "email", "role", "email_verified")}),
                ("Access", {"fields": ("is_active", "is_staff", "is_superuser", "password1", "password2")}),
            )
        return (
            ("Profile", {"fields": ("name", "email", "avatar_url", "role", "email_verified")}),
            ("Access", {"fields": ("is_active", "is_staff", "is_superuser", "local_password")}),
            ("Authentication details", {"classes": ("collapse",), "fields": ("auth0_id", "password_hash", "last_login", "last_login_at")}),
            ("Record details", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
        )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    max_num = 0
    fields = ("product_name", "product_sku", "unit_price", "quantity", "line_total")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    max_num = 0
    fields = ("provider", "amount", "currency", "status", "checkout_session_id", "payment_intent_id", "transaction_id", "paid_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    max_num = 0
    fields = ("from_status", "to_status", "note", "created_at")
    readonly_fields = fields
    verbose_name_plural = "Status history"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "total", "payment_status", "order_status", "created_at")
    list_filter = ("payment_status", "order_status", "created_at")
    search_fields = ("order_number", "customer__email")
    list_select_related = ("customer",)
    list_per_page = 25
    readonly_fields = ("order_number", "customer", "subtotal", "discount_total", "shipping_total", "tax_total", "total", "currency", "shipping_address", "billing_address", "placed_at", "created_at", "updated_at")
    inlines = [OrderItemInline, PaymentInline, OrderStatusHistoryInline]
    fieldsets = (
        ("Order", {"fields": ("order_number", "customer", "order_status", "payment_status", "customer_note")}),
        ("Totals", {"fields": ("subtotal", "discount_total", "shipping_total", "tax_total", "total", "currency")}),
        ("Delivery", {"fields": ("shipping_address", "billing_address")}),
        ("Record details", {"classes": ("collapse",), "fields": ("placed_at", "created_at", "updated_at")}),
    )

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        previous = Order.objects.filter(pk=obj.pk).values_list("order_status", flat=True).first() if change else None
        super().save_model(request, obj, form, change)
        if previous and previous != obj.order_status:
            OrderStatusHistory.objects.create(
                order=obj,
                changed_by=request.user,
                from_status=previous,
                to_status=obj.order_status,
            )
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


# These records are still retained in MySQL and created by the application.
# They are intentionally not registered as top-level admin menu items.
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

admin.site.site_header = "Smart Commerce Administration"
admin.site.site_title = "Smart Commerce"
admin.site.index_title = "Store operations"