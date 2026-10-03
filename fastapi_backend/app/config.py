import os
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


class Settings:
    app_env = os.getenv("APP_ENV", "development")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    django_url = os.getenv("DJANGO_URL", "http://localhost:8001")
    auth_mode = os.getenv("AUTH_MODE", "local").lower()
    jwt_secret_key = os.getenv(
        "JWT_SECRET_KEY", "local-development-secret-change-before-sharing"
    )
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    auth0_domain = os.getenv("AUTH0_DOMAIN", "")
    auth0_audience = os.getenv("AUTH0_AUDIENCE", "")
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_currency = os.getenv("STRIPE_CURRENCY", "inr").lower()
    stripe_demo_mode = os.getenv("STRIPE_DEMO_MODE", "false").lower() == "true"
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")


@lru_cache
def get_settings() -> Settings:
    return Settings()
