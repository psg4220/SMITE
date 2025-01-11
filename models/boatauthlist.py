from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class BoatAuthList(Base):
    __tablename__ = 'boatauthlist'

    boat_id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False, unique=True)
    currency_id = Column(Integer, ForeignKey('currency.currency_id'), nullable=False, unique=True)
    token = Column(String(255), nullable=False)

    currency = relationship("Currency", back_populates="auth_list")
