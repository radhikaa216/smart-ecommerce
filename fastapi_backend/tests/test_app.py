from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_contains_core_customer_routes():
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/products" in paths
    assert "/api/v1/cart" in paths
    assert "/api/v1/checkout/create-session" in paths
    assert "/api/v1/orders" in paths


def test_cart_requires_authentication():
    response = client.get("/api/v1/cart")
    assert response.status_code == 401
