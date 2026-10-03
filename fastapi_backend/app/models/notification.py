from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(60), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSON, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
