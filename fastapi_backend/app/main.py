from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import auth, cart, catalog, checkout, notifications, orders


settings = get_settings()
app = FastAPI(
    title="Smart E-Commerce API",
    version="1.0.0",
    description="Customer-facing API for the local Smart E-Commerce demonstration.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(catalog.router, prefix=api_prefix)
app.include_router(cart.router, prefix=api_prefix)
app.include_router(checkout.router, prefix=api_prefix)
app.include_router(orders.router, prefix=api_prefix)
app.include_router(notifications.router, prefix=api_prefix)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "fastapi", "auth_mode": settings.auth_mode}


@app.get("/", include_in_schema=False)
def home():
    return {"message": "Smart E-Commerce API", "docs": "/docs", "health": "/health"}
