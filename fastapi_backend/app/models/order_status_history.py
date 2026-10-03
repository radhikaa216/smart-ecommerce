from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from app.database import Base


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=False)
    changed_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    from_status = Column(String(40), nullable=True)
    to_status = Column(String(40), nullable=False)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
