from sqlalchemy import BigInteger, Column, DateTime, DECIMAL, Enum, ForeignKey, String
from sqlalchemy.sql import func

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=False)
    provider = Column(Enum("stripe"), nullable=False, default="stripe")
    amount = Column(DECIMAL(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    payment_method = Column(String(80), nullable=True)
    checkout_session_id = Column(String(255), unique=True, nullable=True)
    payment_intent_id = Column(String(255), unique=True, nullable=True)
    transaction_id = Column(String(255), unique=True, nullable=True)
    status = Column(
        Enum("pending", "processing", "succeeded", "failed", "cancelled", "partially_refunded", "refunded"),
        nullable=False,
        default="pending",
    )
    failure_code = Column(String(100), nullable=True)
    failure_message = Column(String(500), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
