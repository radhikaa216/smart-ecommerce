from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from passlib.context import CryptContext

from core.models import Category, Customer, Product


class Command(BaseCommand):
    help = "Create idempotent local demonstration users and products"

    def handle(self, *args, **options):
        admin_model = get_user_model()
        if not admin_model.objects.filter(email="admin@example.com").exists():
            admin_model.objects.create_superuser(email="admin@example.com", password="admin123", name="admin")
            self.stdout.write(self.style.WARNING("Created local Django admin: admin@example.com / admin123"))

        password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        customer, created = Customer.objects.get_or_create(
            email="customer@example.com",
            defaults={"name": "Demo Customer", "password_hash": password_context.hash("customer123"), "email_verified": True},
        )
        if created:
            self.stdout.write(self.style.WARNING("Created local customer: customer@example.com / customer123"))

        data = {
            "Electronics": [
                ("Aurora Wireless Headphones", "AUD-1001", "Immersive audio with active noise cancellation.", "8999.00", 18),
                ("Pulse Smart Watch", "WAT-2001", "Fitness, sleep, and notification tracking.", "6499.00", 8),
            ],
            "Home": [
                ("Luma Desk Lamp", "HOM-3001", "Dimmable LED task light with warm and cool modes.", "2499.00", 4),
                ("Brew Pour-over Set", "HOM-3002", "A complete glass coffee brewing set.", "1799.00", 22),
            ],
            "Accessories": [
                ("Transit Everyday Backpack", "ACC-4001", "Weather-resistant backpack for work and travel.", "3299.00", 12),
                ("Orbit Charging Stand", "ACC-4002", "Minimal wireless charging stand.", "2199.00", 3),
            ],
        }
        for category_name, products in data.items():
            category, _ = Category.objects.get_or_create(name=category_name, defaults={"slug": slugify(category_name)})
            for name, sku, description, price, stock in products:
                Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "category": category, "name": name, "slug": slugify(name),
                        "description": description, "price": Decimal(price), "stock": stock,
                    },
                )
        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
