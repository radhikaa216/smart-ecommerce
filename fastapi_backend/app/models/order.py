from sqlalchemy import BigInteger, Column, DateTime, DECIMAL, Enum, ForeignKey, JSON, String
from sqlalchemy.sql import func

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    order_number = Column(String(40), unique=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    subtotal = Column(DECIMAL(12, 2), nullable=False)
    discount_total = Column(DECIMAL(12, 2), nullable=False, default=0)
    shipping_total = Column(DECIMAL(12, 2), nullable=False, default=0)
    tax_total = Column(DECIMAL(12, 2), nullable=False, default=0)
    total = Column(DECIMAL(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    payment_status = Column(
        Enum("pending", "processing", "paid", "failed", "partially_refunded", "refunded"),
        nullable=False,
        default="pending",
    )
    order_status = Column(
        Enum("pending_payment", "confirmed", "processing", "shipped", "delivered", "cancelled", "refunded"),
        nullable=False,
        default="pending_payment",
    )
    shipping_address = Column(JSON, nullable=False)
    billing_address = Column(JSON, nullable=True)
    customer_note = Column(String(1000), nullable=True)
    placed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
