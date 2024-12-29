# models/transaction.py

from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .base import Base


class Transaction(Base):
    __tablename__ = 'transaction'

    uuid = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_account_id = Column(Integer, ForeignKey('account.account_id'), nullable=False)
    receiver_account_id = Column(Integer, ForeignKey('account.account_id'), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)

    # Relationships to other models
    sender = relationship("Account", foreign_keys=[sender_account_id])
    receiver = relationship("Account", foreign_keys=[receiver_account_id])