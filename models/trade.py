from sqlalchemy import Column, Integer, ForeignKey, Enum, Numeric, BigInteger, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from .base import Base


class TradeType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(enum.Enum):
    LIMIT = "limit",
    MARKET = "market"
    P2P = "P2P"

class TradeStatus(enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELED = "CANCELED"

class TradeList(Base):
    __tablename__ = "trade_list"

    trade_id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(BigInteger, nullable=False)
    base_currency_id = Column(Integer, ForeignKey("currency.currency_id"), nullable=False)
    quote_currency_id = Column(Integer, ForeignKey("currency.currency_id"), nullable=False)
    type = Column(Enum(TradeType), nullable=False)
    price_offered = Column(Numeric(precision=18, scale=8), nullable=False)
    amount = Column(Numeric(precision=18, scale=8), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(TradeStatus), nullable=False, default=TradeStatus.OPEN)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    executed_at = Column(DateTime, nullable=True)
    executed_price = Column(Numeric(precision=18, scale=8), nullable=True)
    recipient_discord_id = Column(BigInteger, nullable=True)  # For P2P orders

    # Relationships to Currency
    base_currency = relationship("Currency", foreign_keys=[base_currency_id])
    quote_currency = relationship("Currency", foreign_keys=[quote_currency_id])

    # Indexing for performance
    __table_args__ = (
        Index('idx_discord_id', 'discord_id'),
        Index('idx_base_quote_currency', 'base_currency_id', 'quote_currency_id'),
    )

