from sqlalchemy import BigInteger, Column, DECIMAL, ForeignKey, Integer, String

from app.database import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(200), nullable=False)
    product_sku = Column(String(80), nullable=False)
    product_image_url = Column(String(2048), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(12, 2), nullable=False)
    line_total = Column(DECIMAL(12, 2), nullable=False)
