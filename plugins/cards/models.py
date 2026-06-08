"""Card batch and card models."""

from sqlalchemy import (
    Column, BigInteger, Integer, DECIMAL, String, DateTime, Text, ForeignKey, func,
)
from app.models import Base


class CardBatch(Base):
    """A batch of generated cards."""

    __tablename__ = "card_batches"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    amount = Column(DECIMAL(14, 6), nullable=False)
    total_count = Column(Integer, default=0)
    redeemed_count = Column(Integer, default=0)
    expires_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())


class Card(Base):
    """A single card code (卡密)."""

    __tablename__ = "cards"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(BigInteger, ForeignKey("card_batches.id"), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 of raw code
    amount = Column(DECIMAL(14, 6), nullable=False)
    status = Column(String(16), default="unused")  # unused / redeemed / expired
    redeemed_by = Column(Integer, ForeignKey("users.id"))
    redeemed_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
