from sqlalchemy import BigInteger, Column, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
