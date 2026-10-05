from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class CustomerManager(BaseUserManager):
    """Manager for the unified storefront and Django-admin user table."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required")
        extra_fields.setdefault("name", email.split("@")[0])
        extra_fields.setdefault("role", "customer")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("name", "Administrator")
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_staff=True and is_superuser=True")
        return self.create_user(email, password, **extra_fields)


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Customer(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    """The single user record for customers, staff, and Django administrators."""

    ROLE_CHOICES = [("customer", "Customer"), ("staff", "Staff"), ("admin", "Admin")]
    auth0_id = models.CharField(max_length=191, unique=True, null=True, blank=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(max_length=254, unique=True)
    # password is Django's password field. password_hash remains for FastAPI's
    # bcrypt local-login compatibility during the staged migration.
    password = models.CharField(max_length=128, blank=True, default="!")
    password_hash = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    avatar_url = models.URLField(max_length=2048, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now, editable=False)

    objects = CustomerManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def save(self, *args, **kwargs):
        if self.role in {"staff", "admin"}:
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False
        if self.is_superuser:
            self.role = "admin"
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} <{self.email}>"

class Address(TimestampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, db_column="user_id", related_name="addresses")
    address_type = models.CharField(max_length=20, default="shipping")
    recipient_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country_code = models.CharField(max_length=2, default="IN")
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "addresses"


class Category(TimestampedModel):
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(TimestampedModel):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    sku = models.CharField(max_length=80, unique=True)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="INR")
    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    sales_count = models.PositiveBigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self):
        return self.stock <= self.low_stock_threshold


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image_url = models.URLField(max_length=2048)
    alt_text = models.CharField(max_length=255, null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_images"
        ordering = ["sort_order"]


class Cart(TimestampedModel):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, db_column="user_id", related_name="cart")

    class Meta:
        db_table = "carts"


class CartItem(TimestampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        db_table = "cart_items"
        constraints = [models.UniqueConstraint(fields=["cart", "product"], name="uq_cart_product")]


class Order(TimestampedModel):
    PAYMENT_STATUSES = [(value, value.replace("_", " ").title()) for value in ["pending", "processing", "paid", "failed", "partially_refunded", "refunded"]]
    ORDER_STATUSES = [(value, value.replace("_", " ").title()) for value in ["pending_payment", "confirmed", "processing", "shipped", "delivered", "cancelled", "refunded"]]
    order_number = models.CharField(max_length=40, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, db_column="user_id", related_name="orders")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUSES, default="pending")
    order_status = models.CharField(max_length=30, choices=ORDER_STATUSES, default="pending_payment")
    shipping_address = models.JSONField()
    billing_address = models.JSONField(null=True, blank=True)
    customer_note = models.CharField(max_length=1000, null=True, blank=True)
    placed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=80)
    product_image_url = models.URLField(max_length=2048, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "order_items"


class Payment(TimestampedModel):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=20, default="stripe")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    payment_method = models.CharField(max_length=80, null=True, blank=True)
    checkout_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    payment_intent_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    status = models.CharField(max_length=30, default="pending")
    failure_code = models.CharField(max_length=100, null=True, blank=True)
    failure_message = models.CharField(max_length=500, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments"


class StockReservation(TimestampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reservations")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default="active")
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "stock_reservations"
        constraints = [models.UniqueConstraint(fields=["order", "product"], name="uq_stock_reservation_order_product")]


class InventoryTransaction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    actor = models.ForeignKey(Customer, on_delete=models.SET_NULL, db_column="actor_user_id", null=True, blank=True)
    transaction_type = models.CharField(max_length=30)
    quantity_delta = models.IntegerField()
    stock_after = models.PositiveIntegerField()
    note = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_transactions"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    changed_by = models.ForeignKey(Customer, on_delete=models.SET_NULL, db_column="changed_by_user_id", null=True, blank=True)
    from_status = models.CharField(max_length=40, null=True, blank=True)
    to_status = models.CharField(max_length=40)
    note = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_status_history"


class Notification(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, db_column="user_id", related_name="notifications")
    notification_type = models.CharField(max_length=60)
    title = models.CharField(max_length=200)
    message = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"


class PaymentWebhookEvent(models.Model):
    provider_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=120)
    payload = models.JSONField()
    processing_status = models.CharField(max_length=20, default="received")
    error_message = models.CharField(max_length=1000, null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_webhook_events"


class EmailDeliveryLog(TimestampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, db_column="user_id", null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    recipient = models.EmailField()
    template_name = models.CharField(max_length=100)
    provider_message_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, default="queued")
    error_message = models.CharField(max_length=1000, null=True, blank=True)

    class Meta:
        db_table = "email_delivery_logs"


class AuditLog(models.Model):
    actor = models.ForeignKey(Customer, on_delete=models.SET_NULL, db_column="actor_user_id", null=True, blank=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=80, null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
