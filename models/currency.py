# models/currency.py
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from .base import Base


class Currency(Base):
    __tablename__ = 'currency'

    currency_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    ticker = Column(String(10), nullable=False, unique=True)
    is_disabled = Column(Boolean, default=False)

    # Define the back-reference for the relationship
    roles = relationship("Role", back_populates="currency")
    accounts = relationship("Account", back_populates="currency")
    auth_list = relationship("BoatAuthList", back_populates="currency")

    def __repr__(self):
        return (
            f"<Currency(currency_id={self.currency_id}, name={self.name}, "
            f"ticker={self.ticker}, is_disabled={self.is_disabled})>"
        )

