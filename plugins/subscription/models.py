"""Subscription plan and subscription models."""

from sqlalchemy import (
    Column, BigInteger, Integer, DECIMAL, String, DateTime, Text, ForeignKey, func,
)
from app.models import Base


class Plan(Base):
    """A subscription plan (套餐)."""

    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    description = Column(Text)
    price_monthly = Column(DECIMAL(14, 6), default=0)
    price_yearly = Column(DECIMAL(14, 6), default=0)
    quota_per_day = Column(BigInteger, default=0)       # token quota
    rate_limit = Column(Integer, default=60)             # RPM
    max_models = Column(Integer, default=0)              # 0 = unlimited
    status = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())


class Subscription(Base):
    """A user's active subscription."""

    __tablename__ = "subscriptions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    period = Column(String(8), default="monthly")    # monthly / yearly
    status = Column(String(16), default="active")    # active / expired / cancelled
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    auto_renew = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
