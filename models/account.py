# models/account.py
from sqlalchemy import Column, Integer, BigInteger, DECIMAL, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .currency import Currency
from .trade import TradeList  # Import TradeList model
from .base import Base


class Account(Base):
    __tablename__ = 'account'

    account_id = Column(Integer, primary_key=True)
    discord_id = Column(BigInteger, unique=False, nullable=False)
    currency_id = Column(Integer, ForeignKey('currency.currency_id'), nullable=False)
    balance = Column(DECIMAL(15, 2), nullable=False, default=0.00)
    is_disabled = Column(Boolean, default=False)

    # Relationship to Currency table
    currency = relationship("Currency", back_populates="accounts")
