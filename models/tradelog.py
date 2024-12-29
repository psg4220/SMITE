from sqlalchemy import Column, Integer, ForeignKey, DECIMAL, Float, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base


class TradeLog(Base):
    __tablename__ = "trade_log"

    trade_log_id = Column(Integer, primary_key=True, autoincrement=True)
    base_currency_id = Column(Integer, ForeignKey('currency.currency_id'), nullable=False)
    quote_currency_id = Column(Integer, ForeignKey('currency.currency_id'), nullable=False)
    price = Column(DECIMAL(precision=18, scale=8), nullable=False)
    date_traded = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    base_currency = relationship("Currency", foreign_keys=[base_currency_id])
    quote_currency = relationship("Currency", foreign_keys=[quote_currency_id])


Index('idx_date_traded', TradeLog.date_traded)
