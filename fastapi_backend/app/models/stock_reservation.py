from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class StockReservation(Base):
    __tablename__ = "stock_reservations"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(Enum("active", "consumed", "released", "expired"), nullable=False, default="active")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("order_id", "product_id", name="uq_stock_reservation_order_product"),)
