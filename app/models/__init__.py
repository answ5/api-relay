"""Core models — SQLAlchemy ORM models for the relay system."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    DECIMAL,
    Enum,
    BigInteger,
    ForeignKey,
    JSON,
    LargeBinary,
    func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(128), default="")
    balance = Column(DECIMAL(14, 4), default=0)
    status = Column(Integer, default=1)
    role = Column(String(16), default="user")  # user / admin / super_admin
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(64), default="")
    key_prefix = Column(String(8), nullable=False)
    key_hash = Column(String(255), nullable=False)
    models = Column(Text, nullable=True)  # JSON array or null=all
    rate_limit_per_minute = Column(Integer, default=60)
    balance_limit = Column(DECIMAL(14, 4), default=0)
    status = Column(Integer, default=1)
    group_name = Column(String(32), default="default")
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    base_url = Column(String(256), nullable=False)
    api_key = Column(String(512), nullable=False)
    weight = Column(Integer, default=10)
    priority = Column(Integer, default=0)
    status = Column(Integer, default=1)
    models = Column(Text, nullable=True)  # JSON array
    circuit_breaker = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ModelPricing(Base):
    __tablename__ = "model_pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(128), nullable=False, unique=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    billing_method = Column(String(16), default="per_token")  # per_token, per_request, per_image
    prompt_token_price_1k = Column(DECIMAL(14, 6), default=0)
    completion_token_price_1k = Column(DECIMAL(14, 6), default=0)
    request_price = Column(DECIMAL(14, 6), default=0)
    image_price_per_generation = Column(DECIMAL(14, 6), nullable=True)
    status = Column(Integer, default=1)
    groups = Column(Text, nullable=True)  # JSON array
    created_at = Column(DateTime, server_default=func.now())


class Log(Base):
    __tablename__ = "logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(String(64), nullable=False)
    user_id = Column(Integer, nullable=False)
    token_id = Column(Integer, nullable=True)
    channel_id = Column(Integer, nullable=True)
    model_name = Column(String(128), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    billing_method = Column(String(16), default="per_token")
    user_cost = Column(DECIMAL(14, 6), default=0)
    upstream_cost = Column(DECIMAL(14, 6), default=0)
    response_ms = Column(Integer, default=0)
    is_stream = Column(Integer, default=0)
    status = Column(String(16), default="success")
    ip = Column(String(45), default="")
    created_at = Column(DateTime, server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(DECIMAL(14, 4), nullable=False)
    type = Column(String(16), nullable=False)  # consume, recharge, refund, admin_adjust
    balance_after = Column(DECIMAL(14, 4))
    note = Column(Text, default="")
    log_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class RequestPayload(Base):
    __tablename__ = "request_payloads"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(String(64), nullable=False, index=True)
    request_body = Column(LargeBinary, nullable=True)
    response_body = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(128), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Integer, default=0)  # 0=unused, 1=used
    created_at = Column(DateTime, server_default=func.now())
