from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, BigInteger
from sqlalchemy.orm import relationship
import enum
from .base import Base


class Role(Base):
    __tablename__ = 'role'

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    currency_id = Column(Integer, ForeignKey("currency.currency_id"), nullable=False)
    discord_id = Column(BigInteger, nullable=False)
    role_number = Column(Integer, nullable=False)

    # Correct the relationship definition
    currency = relationship("Currency", back_populates="roles", foreign_keys=[currency_id])
