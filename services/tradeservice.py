from pandas.core.dtypes.cast import maybe_cast_to_datetime
from sqlalchemy.future import select
from sqlalchemy import func, update
from sqlalchemy import and_
from db import get_session
from models.account import Account
from models.trade import TradeList, TradeType, OrderType, TradeStatus
from services.accountservice import AccountService
from services.currencyservice import CurrencyService
from services.tradelogservice import TradeLogService
from decimal import Decimal
from math import ceil


class TradeService:

    @staticmethod
    async def create_trade(
            discord_id: int,
            base_currency_id: int,
            quote_currency_id: int,
            trade_type: TradeType,
            price_offered: Decimal,
            amount: Decimal,
            order_type: OrderType = OrderType.LIMIT,
            status: TradeStatus = TradeStatus.OPEN,  # Default status to OPEN
            executed_at: str | None = None,  # Optional field
            executed_price: Decimal | None = None,  # Optional field
    ) -> TradeList | None:
        """
        Creates a new trade in the system with all trade parameters.

        Args:
            discord_id (int): ID of the Discord user creating the trade.
            base_currency_id (int): ID of the base currency.
            quote_currency_id (int): ID of the quote currency.
            trade_type (TradeType): Type of the trade (BUY or SELL).
            price_offered (Decimal): Offered price for the trade.
            amount (Decimal): Amount involved in the trade.
            order_type (OrderType): The type of order (LIMIT, MARKET, P2P).
            status (TradeStatus): The status of the trade (default is 'OPEN').
            executed_at (str | None): The timestamp when the trade was executed (optional).
            executed_price (Decimal | None): The price at which the trade was executed (optional).

        Returns:
            TradeList | None: The newly created trade, or None if creation fails.
        """
        # Validate the inputs
        if price_offered <= 0 or amount <= 0:
            raise ValueError("Price offered and amount must be greater than zero.")

        if base_currency_id == quote_currency_id:
            raise ValueError("Base currency and quote currency must be different.")

        # Create the trade asynchronously
        async with get_session() as session:
            try:
                new_trade = TradeList(
                    discord_id=discord_id,
                    base_currency_id=base_currency_id,
                    quote_currency_id=quote_currency_id,
                    type=trade_type,
                    price_offered=price_offered,
                    amount=amount,
                    order_type=order_type,
                    status=status,
                    executed_at=executed_at,
                    executed_price=executed_price,
                )
                session.add(new_trade)
                await session.commit()
                await session.refresh(new_trade)
                return new_trade

            except Exception as e:
                # Log or handle any exceptions that occur during trade creation
                print(f"Error creating trade: {e}")
                await session.rollback()
                return None

    @staticmethod
    async def read_trade_by_id(trade_id: int):
        """
        Retrieves a trade by its ID.

        Args:
            trade_id (int): The trade ID.

        Returns:
            TradeList: The trade with the specified ID, or None if not found.
        """
        async with get_session() as session:
            result = await session.execute(select(TradeList).filter(TradeList.trade_id == trade_id))
            return result.scalars().first()

    @staticmethod
    async def update_trade(
            trade_id: int,
            new_price_offered: Decimal = None,
            new_amount: Decimal = None,
    ):
        """
        Updates the details of a specific trade.

        Args:
            trade_id (int): The trade ID.
            new_price_offered (Decimal, optional): The new price offered.
            new_amount (Decimal, optional): The new trade amount.

        Returns:
            TradeList: The updated trade, or None if not found.
        """
        async with get_session() as session:
            result = await session.execute(select(TradeList).filter(TradeList.trade_id == trade_id))
            trade = result.scalars().first()
            if trade:
                if new_price_offered is not None:
                    trade.price_offered = new_price_offered
                if new_amount is not None:
                    trade.amount = new_amount
                await session.commit()
                return trade
            return None

    @staticmethod
    async def set_status(trade_id: int, status: TradeStatus) -> None:
        """
        Updates the status of a trade for the given discord_id, base_currency_id, and quote_currency_id.

        Args:
            trade_id (str): The trade id
            status (str): The new status to set.

        Returns:
            None
        """
        async with get_session() as session:  # Create a session
            query = (
                select(TradeList)
                .where(
                    TradeList.trade_id == trade_id
                )
            )
            result = await session.execute(query)
            trade = result.scalar_one_or_none()

            if trade:  # If a trade exists, update its status
                trade.status = status
                await session.commit()

    @staticmethod
    async def get_status(trade_id: int) -> str | None:
        """
        Fetches the status of a trade for the given discord_id, base_currency_id, and quote_currency_id.

        Args:
            trade_id (int): The trade id

        Returns:
            str | None: The status of the trade, or None if no trade is found.
        """
        async with get_session() as session:  # Create a session
            query = (
                select(TradeList.status)
                .where(
                    TradeList.trade_id == trade_id
                )
            )
            result = await session.execute(query)
            status = result.scalar_one_or_none()  # Get the single column result (status)

            return status  # Return the status, or None if no result


    @staticmethod
    async def delete_trade(trade_id: int):
        """
        Deletes a trade by its ID.

        Args:
            trade_id (int): The trade ID.

        Returns:
            bool: True if the trade was deleted, False otherwise.
        """
        async with get_session() as session:
            result = await session.execute(select(TradeList).filter(TradeList.trade_id == trade_id))
            trade = result.scalars().first()
            if trade:
                await session.delete(trade)
                await session.commit()
                return True
            return False

    @staticmethod
    async def get_bid_price(base_currency_id: int, quote_currency_id: int):
        """
        Get the highest bid price for the given currency pair.

        :param base_currency_id: ID of the base currency.
        :param quote_currency_id: ID of the quote currency.
        :return: Highest bid price (Decimal).
        """
        async with get_session() as session:
            result = await session.execute(
                select(func.max(TradeList.price_offered))
                .where(TradeList.base_currency_id == base_currency_id)
                .where(TradeList.quote_currency_id == quote_currency_id)
                .where(TradeList.status == TradeStatus.OPEN)
            )
            bid_price = result.scalar()
            return Decimal(bid_price) if bid_price is not None else Decimal(0)

    @staticmethod
    async def get_ask_price(base_currency_id: int, quote_currency_id: int):
        """
        Get the lowest ask price for the given currency pair.

        :param base_currency_id: ID of the base currency.
        :param quote_currency_id: ID of the quote currency.
        :return: Lowest ask price (Decimal).
        """
        async with get_session() as session:
            result = await session.execute(
                select(func.min(TradeList.price_offered))
                .where(TradeList.base_currency_id == base_currency_id)
                .where(TradeList.quote_currency_id == quote_currency_id)
                .where(TradeList.status == TradeStatus.OPEN)
            )
            ask_price = result.scalar()
            return Decimal(ask_price) if ask_price is not None else Decimal(0)

    @staticmethod
    async def get_all_trades(
            discord_id: int = None,
            base_currency_id: int = None,
            quote_currency_id: int = None,
            trade_type: TradeType = None,
            status: TradeStatus = None,
            page: int = 1,
            limit: int = 10,
    ):
        """
        Retrieves trades with optional filtering and pagination.

        Args:
            base_currency_id (int, optional): Filter by base currency ID.
            quote_currency_id (int, optional): Filter by quote currency ID.
            trade_type (TradeType, optional): Filter by trade type (BUY or SELL).
            page (int, optional): The page number (default is 1).
            limit (int, optional): The number of trades per page (default is 10).

        Returns:
            list: A list of TradeList objects matching the criteria.
        """
        async with get_session() as session:
            query = select(TradeList)

            # Apply filters if provided
            if discord_id:
                query = query.where(TradeList.discord_id == discord_id)
            if base_currency_id:
                query = query.where(TradeList.base_currency_id == base_currency_id)
            if quote_currency_id:
                query = query.where(TradeList.quote_currency_id == quote_currency_id)
            if trade_type:
                query = query.where(TradeList.type == trade_type)
            if status:
                query = query.where(TradeList.status == status)

            # Apply sorting based on trade type
            if trade_type == TradeType.BUY:
                query = query.order_by(TradeList.price_offered.asc())
            elif trade_type == TradeType.SELL:
                query = query.order_by(TradeList.price_offered.desc())

            # Apply pagination
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            return result.scalars().all()

    @staticmethod
    async def get_total_pages(
        discord_id: int = None,
        base_currency_id: int = None,
        quote_currency_id: int = None,
        trade_type: TradeType = None,
        status: TradeStatus = None,
        limit: int = 10
    ) -> int:
        """
        Calculate the total number of pages for the given filters.

        Args:
            discord_id (int): The Discord ID of the user (optional).
            base_currency_id (int): The ID of the base currency (optional).
            quote_currency_id (int): The ID of the quote currency (optional).
            trade_type (TradeType): The type of the trade (optional).
            status (TradeStatus): The status of the trade (optional).

        Returns:
            int: Total number of pages.
            :param limit: Number of rows per page
        """
        async with get_session() as session:
            # Base query
            query = select(func.count()).select_from(TradeList)

            # Apply filters dynamically based on provided arguments
            if discord_id is not None:
                query = query.where(TradeList.discord_id == discord_id)
            if base_currency_id is not None:
                query = query.where(TradeList.base_currency_id == base_currency_id)
            if quote_currency_id is not None:
                query = query.where(TradeList.quote_currency_id == quote_currency_id)
            if trade_type is not None:
                query = query.where(TradeList.type == trade_type)
            if status is not None:
                query = query.where(TradeList.status == status)

            # Execute the query
            result = await session.execute(query)
            total_trades = result.scalar()  # Extract the total count

            # Calculate total pages based on PAGE_SIZE
            total_pages = ceil(total_trades / limit) if total_trades else 1
            return total_pages

    @staticmethod
    async def cancel_trade(trade_id: int) -> bool:
        """
        Cancels a trade by marking its status as 'CANCELLED'.

        Args:
            trade_id (int): The trade ID.

        Returns:
            bool: True if the trade was successfully cancelled, False otherwise.
        """
        async with get_session() as session:
            result = await session.execute(select(TradeList).filter(TradeList.trade_id == trade_id))
            trade = result.scalars().first()

            if trade and trade.status == TradeStatus.OPEN:
                # Set the trade status to CANCELED
                trade.status = TradeStatus.CANCELED
                await session.commit()

                # Reverse any reserved funds for the cancelled trade
                if trade.type == TradeType.BUY:
                    # Refund the reserved quote currency
                    trader_account = await AccountService.get_account(trade.discord_id, trade.quote_currency_id)
                    if trader_account:
                        refund_amount = trade.price_offered * trade.amount
                        await AccountService.update_account_balance(
                            trader_account.account_id,
                            trader_account.balance + refund_amount
                        )
                elif trade.type == TradeType.SELL:
                    # Refund the reserved base currency
                    trader_account = await AccountService.get_account(trade.discord_id, trade.base_currency_id)
                    if trader_account:
                        await AccountService.update_account_balance(
                            trader_account.account_id,
                            trader_account.balance + trade.amount
                        )
                return True

            return False

    @staticmethod
    async def find_matching_trade(
            discord_id: int,
            base_currency_id: int,
            quote_currency_id: int,
            trade_type: TradeType,
            price_offered: Decimal,
            amount: Decimal,
            order_type: OrderType = OrderType.LIMIT
    ) -> TradeList:
        """
        Finds a matching trade based on the criteria.

        Args:
            discord_id (int): Discord ID of the trader (to exclude their own trades).
            base_currency_id (int): Base currency ID of the trade.
            quote_currency_id (int): Quote currency ID of the trade.
            trade_type (TradeType): Type of trade (BUY or SELL).
            price_offered (Decimal): Price offered for the trade.
            amount (Decimal): Amount to trade.
            order_type (OrderType): The type of order (default. LIMIT)

        Returns:
            TradeList: The first matching trade, or None if no match found.
        """
        # Determine the opposite trade type
        opposite_trade_type = TradeType.BUY if trade_type == TradeType.SELL else TradeType.SELL

        async with get_session() as session:
            # Build the query
            query = (
                select(TradeList)
                .filter(
                    TradeList.discord_id != discord_id,  # Exclude the user's own trades
                    TradeList.order_type == order_type,
                    TradeList.status == TradeStatus.OPEN,
                    TradeList.base_currency_id == base_currency_id,
                    TradeList.quote_currency_id == quote_currency_id,
                    TradeList.type == opposite_trade_type,
                    TradeList.price_offered >= price_offered if trade_type == TradeType.SELL else TradeList.price_offered <= price_offered,
                    TradeList.amount > 0,
                )
                .order_by(
                    TradeList.price_offered.asc() if trade_type == TradeType.BUY else TradeList.price_offered.desc())
                .limit(1)
            )

            # Execute the query
            result = await session.execute(query)
            return result.scalars().first()

    @staticmethod
    async def process_trade(discord_id: int, base_currency_id: int, quote_currency_id: int,
                            trade_type: TradeType, price: Decimal, amount: Decimal) -> int:
        """
        Processes a trade by finding matching trades and subtracting amounts accordingly.

        :param int discord_id: The trader's Discord ID.
        :param int base_currency_id: The base currency ID.
        :param int quote_currency_id: The quote currency ID.
        :param TradeType trade_type: Type of trade (BUY or SELL).
        :param Decimal price: Price offered for the trade.
        :param Decimal amount: Amount to be traded.
        :returns: Status code indicating the result of the trade:
                  1 - Trade fully fulfilled,
                  2 - Trade partially fulfilled and listed,
                  3 - Insufficient balance.
                  4 - Accounts are disabled
        """
        opposite_trade_type = TradeType.BUY if trade_type == TradeType.SELL else TradeType.SELL
        remaining_amount = Decimal(amount)

        async with get_session() as session:
            # Fetch the trader's accounts
            trader_base_account = await session.execute(
                select(Account).where(Account.discord_id == discord_id, Account.currency_id == base_currency_id)
            )
            trader_base_account = trader_base_account.scalars().first()

            trader_quote_account = await session.execute(
                select(Account).where(Account.discord_id == discord_id, Account.currency_id == quote_currency_id)
            )
            trader_quote_account = trader_quote_account.scalars().first()

            # Ensure accounts exist
            if not trader_base_account:
                trader_base_account = Account(discord_id=discord_id, currency_id=base_currency_id,
                                              balance=Decimal("0.00"))
                session.add(trader_base_account)

            if not trader_quote_account:
                trader_quote_account = Account(discord_id=discord_id, currency_id=quote_currency_id,
                                               balance=Decimal("0.00"))
                session.add(trader_quote_account)

            await session.commit()

            # Check if accounts are disabled:
            if trader_base_account.is_disabled or trader_quote_account.is_disabled:
                return 4

            # Verify balance before processing
            if trade_type == TradeType.SELL:
                if trader_base_account.balance < amount:
                    return 3  # Insufficient base currency balance
            elif trade_type == TradeType.BUY:
                if trader_quote_account.balance < amount * price:
                    return 3  # Insufficient quote currency balance

            # Process trades in batches
            while remaining_amount > 0:
                matching_trades_result = await session.execute(
                    select(
                        TradeList.trade_id,
                        TradeList.amount,
                        TradeList.price_offered,
                        TradeList.discord_id
                    )
                    .where(
                        TradeList.discord_id != discord_id,
                        TradeList.base_currency_id == base_currency_id,
                        TradeList.quote_currency_id == quote_currency_id,
                        TradeList.type == opposite_trade_type,
                        (
                            TradeList.price_offered >= price if trade_type == TradeType.SELL else TradeList.price_offered <= price
                        ),
                        TradeList.status == TradeStatus.OPEN
                    )
                    .order_by(
                        TradeList.price_offered.asc() if trade_type == TradeType.SELL else TradeList.price_offered.desc(),
                        TradeList.created_at
                    )
                    .limit(10)
                )
                matching_trades = matching_trades_result.mappings().all()

                if not matching_trades:
                    break

                updates = []
                for trade in matching_trades:
                    if remaining_amount <= 0:
                        break

                    trade_id = trade["trade_id"]
                    trade_amount = trade["amount"]
                    counterparty_id = trade["discord_id"]
                    counterparty_price = trade["price_offered"]

                    # Fetch counterparty accounts
                    counterparty_base_account = await session.execute(
                        select(Account).where(Account.discord_id == counterparty_id,
                                              Account.currency_id == base_currency_id)
                    )
                    counterparty_base_account = counterparty_base_account.scalars().first()

                    counterparty_quote_account = await session.execute(
                        select(Account).where(Account.discord_id == counterparty_id,
                                              Account.currency_id == quote_currency_id)
                    )
                    counterparty_quote_account = counterparty_quote_account.scalars().first()

                    # Ensure accounts exist
                    if not counterparty_base_account:
                        counterparty_base_account = Account(discord_id=counterparty_id, currency_id=base_currency_id,
                                                            balance=Decimal("0.00"))
                        session.add(counterparty_base_account)

                    if not counterparty_quote_account:
                        counterparty_quote_account = Account(discord_id=counterparty_id, currency_id=quote_currency_id,
                                                             balance=Decimal("0.00"))
                        session.add(counterparty_quote_account)

                    await session.commit()

                    if trade_amount <= remaining_amount:
                        # Fully consume this trade
                        remaining_amount -= trade_amount
                        updates.append({
                            "trade_id": trade_id,
                            "new_amount": Decimal("0"),
                            "status": TradeStatus.CLOSED
                        })

                        # Update balances
                        if trade_type == TradeType.SELL:
                            trader_base_account.balance -= trade_amount
                            trader_quote_account.balance += trade_amount * trade["price_offered"]
                            counterparty_base_account.balance += trade_amount
                            counterparty_quote_account.balance -= trade_amount * trade["price_offered"]
                        else:
                            trader_base_account.balance += trade_amount
                            trader_quote_account.balance -= trade_amount * trade["price_offered"]
                            counterparty_base_account.balance -= trade_amount
                            counterparty_quote_account.balance += trade_amount * trade["price_offered"]

                        # Log the price
                        await TradeLogService.create_trade_log(base_currency_id, quote_currency_id, counterparty_price)

                    else:
                        # Partially consume this trade
                        updates.append({
                            "trade_id": trade_id,
                            "new_amount": trade_amount - remaining_amount,
                            "status": TradeStatus.OPEN
                        })

                        # Update balances
                        if trade_type == TradeType.SELL:
                            trader_base_account.balance -= remaining_amount
                            trader_quote_account.balance += remaining_amount * trade["price_offered"]
                            counterparty_base_account.balance += remaining_amount
                            counterparty_quote_account.balance -= remaining_amount * trade["price_offered"]
                        else:
                            trader_base_account.balance += remaining_amount
                            trader_quote_account.balance -= remaining_amount * trade["price_offered"]
                            counterparty_base_account.balance -= remaining_amount
                            counterparty_quote_account.balance += remaining_amount * trade["price_offered"]

                        remaining_amount = Decimal("0")

                        # Log the price
                        await TradeLogService.create_trade_log(base_currency_id, quote_currency_id, counterparty_price)

                # Batch update trades in the database
                for update_data in updates:
                    stmt = (
                        update(TradeList)
                        .where(TradeList.trade_id == update_data["trade_id"])
                        .values(
                            amount=update_data["new_amount"],
                            status=update_data["status"],
                            updated_at=func.now()
                        )
                    )

                    await session.execute(stmt)

                await session.commit()

            # If there is any remaining amount, create a new trade
            if remaining_amount > 0:
                new_trade = TradeList(
                    discord_id=discord_id,
                    base_currency_id=base_currency_id,
                    quote_currency_id=quote_currency_id,
                    type=trade_type,
                    price_offered=price,
                    amount=remaining_amount,
                    order_type=OrderType.LIMIT,
                    status=TradeStatus.OPEN
                )
                session.add(new_trade)
                await session.commit()
                return 2  # Trade partially fulfilled and listed

            return 1  # Trade fully fulfilled

    @staticmethod
    async def peer_trade(
        base_currency_id: int,
        quote_currency_id: int,
        sender_discord_id: int,
        receiver_discord_id: int,
        sender_amount: Decimal,
        receiver_amount: Decimal
    ):
        """
        Handles a peer-to-peer trade between two users.

        Args:
            base_currency_id (int): ID of the base currency being traded.
            quote_currency_id (int): ID of the quote currency being traded.
            sender_discord_id (int): Discord ID of the sender.
            receiver_discord_id (int): Discord ID of the receiver.
            sender_amount (Decimal): Amount of the base currency the sender is offering.
            receiver_amount (Decimal): Amount of the quote currency the receiver is offering.

        Returns:
            Union[int, TradeList]:
                - TradeList: The created TradeList object if the trade succeeds.
                - int: Error codes for failures.

        Error Codes:
            1: One or both currencies do not exist.
            2: Sender does not have sufficient balance.
            3: Receiver's account does not exist.
            4: Unexpected error during trade.
        """
        async with get_session() as session:
            try:
                # Validate currencies
                currencies = await session.execute(
                    select(Currency).where(Currency.currency_id.in_([base_currency_id, quote_currency_id]))
                )
                currencies = currencies.scalars().all()
                if len(currencies) != 2:
                    return 1  # Error Code: 1

                # Validate sender's account and balance
                sender_account = await session.execute(
                    select(Account).where(
                        Account.discord_id == sender_discord_id,
                        Account.currency_id == base_currency_id
                    )
                )
                sender_account = sender_account.scalar_one_or_none()
                if not sender_account or sender_account.balance < sender_amount:
                    return 2  # Error Code: 2

                # Validate receiver's account
                receiver_account = await session.execute(
                    select(Account).where(
                        Account.discord_id == receiver_discord_id,
                        Account.currency_id == quote_currency_id
                    )
                )
                receiver_account = receiver_account.scalar_one_or_none()
                if not receiver_account:
                    return 3  # Error Code: 3

                # Perform balance updates
                sender_account.balance -= sender_amount
                receiver_account.balance += receiver_amount

                # Create trade record
                trade = TradeList(
                    discord_id=sender_discord_id,
                    recipient_discord_id=receiver_discord_id,
                    base_currency_id=base_currency_id,
                    quote_currency_id=quote_currency_id,
                    type=TradeType.SELL,
                    price_offered=receiver_amount / sender_amount,  # Implied price
                    amount=sender_amount,
                    order_type=OrderType.P2P,
                    status=TradeStatus.CLOSED,
                    created_at=datetime.utcnow(),
                    executed_at=datetime.utcnow(),
                    executed_price=receiver_amount / sender_amount,
                )
                session.add(trade)

                # Commit the transaction
                await session.commit()

                return trade  # Return the created trade object
            except Exception as e:
                await session.rollback()
                print(f"Unexpected error during trade: {e}")  # Replace with proper logging
                return 4  # Error Code: 4