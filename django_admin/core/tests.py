from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


class ProductModelTests(TestCase):
    def test_low_stock_uses_configured_threshold(self):
        category = Category.objects.create(name="Home", slug="home")
        product = Product.objects.create(
            category=category, name="Lamp", slug="lamp", sku="LAMP-1",
            price="1000.00", stock=3, low_stock_threshold=5,
        )
        self.assertTrue(product.is_low_stock)


class DashboardTests(TestCase):
    def test_dashboard_requires_staff_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_view_dashboard(self):
        user = get_user_model().objects.create_user("staff", password="password", is_staff=True)
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operations dashboard")
