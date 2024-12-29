from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.exc import NoResultFound
from models import TradeList, TradeLog
from db import get_session
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import numpy as np


class TradeLogService:
    @staticmethod
    async def calculate_percentage_change(prices):
        """Calculates the percentage change between consecutive prices in an array.

        Args:
          prices: A list or NumPy array of prices.

        Returns:
          A list of percentage changes.
        """
        try:
            price_changes = np.diff(prices) / prices[:-1] * 100
            return price_changes.tolist()
        except ZeroDivisionError:
            return [0]

    @staticmethod
    async def calculate_percentage(base_currency_id: int, quote_currency_id: int, time_delta: timedelta):
        """
        Calculate the percentage change for a currency pair within a specified time delta.

        :param base_currency_id: ID of the base currency.
        :param quote_currency_id: ID of the quote currency.
        :param time_delta: Time range for the calculation (e.g., last 24 hours).
        :return: A list of percentage changes or an empty list if no data is found.
        """
        async with get_session() as session:
            # Calculate the time threshold
            last_trade = await TradeLogService.get_last_trade_log(base_currency_id, quote_currency_id)
            time_threshold = last_trade.date_traded - time_delta

            # Query for prices within the time range
            result = await session.execute(
                select(TradeLog.price)
                .where(TradeLog.base_currency_id == base_currency_id)
                .where(TradeLog.quote_currency_id == quote_currency_id)
                .where(TradeLog.date_traded >= time_threshold)
                .order_by(TradeLog.date_traded)
            )
            prices = [row[0] for row in result.fetchall()]

            # Calculate percentage changes if prices exist
            if prices:
                return await TradeLogService.calculate_percentage_change(prices)

            return []

    @staticmethod
    async def create_trade_log(base_currency_id, quote_currency_id, price, date_traded=None):
        """
        Creates a new trade log entry.

        :param base_currency_id: ID of the base currency.
        :param quote_currency_id: ID of the quote currency.
        :param price: The price of the trade.
        :param date_traded: The date and time the trade occurred (default: now).
        :return: The created TradeLog instance.
        """
        async with get_session() as session:
            new_trade = TradeLog(
                base_currency_id=base_currency_id,
                quote_currency_id=quote_currency_id,
                price=price,
                date_traded=date_traded or datetime.now(timezone.utc)
            )
            session.add(new_trade)
            await session.commit()
            return new_trade

    @staticmethod
    async def get_trade_log_by_id(trade_log_id):
        """
        Retrieves a trade log by its ID.

        :param trade_log_id: The ID of the trade log.
        :return: The TradeLog instance, or None if not found.
        """
        async with get_session() as session:
            stmt = select(TradeLog).where(TradeLog.trade_log_id == trade_log_id)
            result = await session.execute(stmt)
            return result.scalars().first()  # Extract the first result

    @staticmethod
    async def get_trade_logs_by_currency_pair(base_currency_id, quote_currency_id, time_delta=None):
        """
        Retrieves trade logs for a specific currency pair, optionally filtering by a time range.

        :param base_currency_id: ID of the base currency.
        :param quote_currency_id: ID of the quote currency.
        :param time_delta: A timedelta object representing the time range (e.g., last 1 day, 8 hours, etc.).
        :return: A list of TradeLog instances.
        """
        async with get_session() as session:
            # Base query
            stmt = (
                select(TradeLog)
                .where(
                    TradeLog.base_currency_id == base_currency_id,
                    TradeLog.quote_currency_id == quote_currency_id,
                )
            )
            last_trade = await TradeLogService.get_last_trade_log(base_currency_id, quote_currency_id)
            # Apply time range filter if time_delta is provided
            if time_delta is not None:
                time_threshold = last_trade.date_traded - time_delta
                stmt = stmt.where(TradeLog.date_traded >= time_threshold)

            stmt = stmt.order_by(TradeLog.date_traded.desc())

            result = await session.execute(stmt)
            return result.scalars().all()  # Extract all results

    @staticmethod
    async def get_last_trade_log(base_currency_id, quote_currency_id):
        """
        Retrieves all trade logs for a specific currency pair.

        :param base_currency_id: ID of the base currency.
        :param quote_currency_id: ID of the quote currency.
        :return: A list of TradeLog instances.
        """
        async with get_session() as session:
            stmt = (
                select(TradeLog)
                .where(
                    TradeLog.base_currency_id == base_currency_id,
                    TradeLog.quote_currency_id == quote_currency_id,
                )
                .order_by(TradeLog.date_traded.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    @staticmethod
    async def update_trade_log(trade_log_id, price):
        """
        Updates the price of a trade log and recalculates the percentage movement.

        :param trade_log_id: The ID of the trade log to update.
        :param price: The new price to set.
        :return: The updated TradeLog instance, or None if not found.
        """
        async with get_session() as session:
            stmt = select(TradeLog).where(TradeLog.trade_log_id == trade_log_id)
            result = await session.execute(stmt)
            trade_log = result.scalars().first()  # Extract the first result

            if trade_log:
                trade_log.price = price
                trade_log.percentage = await TradeLogService.calculate_percentage(
                    trade_log.base_currency_id, trade_log.quote_currency_id, price
                )
                await session.commit()
                return trade_log
            return None

    @staticmethod
    async def delete_trade_log(trade_log_id):
        """
        Deletes a trade log by its ID.

        :param trade_log_id: The ID of the trade log to delete.
        :return: True if the trade log was deleted, False if not found.
        """
        async with get_session() as session:
            stmt = select(TradeLog).where(TradeLog.trade_log_id == trade_log_id)
            result = await session.execute(stmt)
            trade_log = result.scalars().first()  # Extract the first result

            if trade_log:
                await session.delete(trade_log)
                await session.commit()
                return True
            return False
