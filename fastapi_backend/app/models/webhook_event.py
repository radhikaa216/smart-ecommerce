from sqlalchemy import BigInteger, Column, DateTime, Enum, JSON, String
from sqlalchemy.sql import func

from app.database import Base


class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    provider_event_id = Column(String(255), unique=True, nullable=False)
    event_type = Column(String(120), nullable=False)
    payload = Column(JSON, nullable=False)
    processing_status = Column(Enum("received", "processed", "failed", "ignored"), nullable=False, default="received")
    error_message = Column(String(1000), nullable=True)
    received_at = Column(DateTime, nullable=False, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)
