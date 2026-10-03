from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, String
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    auth0_id = Column(String(191), unique=True, nullable=True)
    name = Column(String(150), nullable=False)
    email = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(Enum("customer", "staff", "admin"), nullable=False, default="customer")
    avatar_url = Column(String(2048), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
