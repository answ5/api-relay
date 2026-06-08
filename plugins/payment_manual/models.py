"""Payment orders — SQLAlchemy model."""

from sqlalchemy import (
    Column, BigInteger, Integer, DECIMAL, String, DateTime, ForeignKey,
    func,
)
from app.models import Base


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(DECIMAL(14, 6), nullable=False)
    bonus = Column(DECIMAL(14, 6), default=0)
    payment_method = Column(String(16), default="manual")  # manual / epay / stripe
    payment_channel = Column(String(32))                  # alipay / wechat
    status = Column(String(16), default="pending")         # pending / paid / failed / refunded
    epay_trade_no = Column(String(128), unique=True, nullable=True)
    epay_url = Column(String(512))
    stripe_pi_id = Column(String(128), unique=True, nullable=True)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
