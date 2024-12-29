from models.transaction import Transaction
from db import get_session
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from services.accountservice import AccountService


class TransactionService:

    @staticmethod
    async def create_transaction(sender_account_id: int, receiver_account_id: int, currency_id: int, amount: float):
        """
        Creates a new transaction in the database.

        Args:
            sender_account_id (int): The ID of the sender's account.
            receiver_account_id (int): The ID of the receiver's account.
            currency_id (int): The ID of the currency used in the transaction.
            amount (float): The transaction amount.

        Returns:
            Transaction: The created Transaction object.
        """
        async with get_session() as session:
            new_transaction = Transaction(
                sender_account_id=sender_account_id,
                receiver_account_id=receiver_account_id,
                currency_id=currency_id,
                amount=amount
            )
            session.add(new_transaction)
            await session.commit()
            await session.refresh(new_transaction)
            return new_transaction

    @staticmethod
    async def read_transaction_by_uuid(transaction_uuid: str):
        """
        Retrieves a transaction by its UUID from the database.

        Args:
            transaction_uuid (str): The UUID of the transaction to retrieve.

        Returns:
            Transaction or None: The Transaction object if found, otherwise None.
        """
        async with get_session() as session:
            result = await session.execute(select(Transaction).filter(Transaction.uuid == transaction_uuid))
            transaction = result.scalars().first()
            return transaction

    @staticmethod
    async def get_transactions_by_account(account_id: int, page: int = 1, limit: int = 10, recent: bool = True):
        """
        Retrieves transactions for a specific account with pagination, sorted by date.

        Args:
            account_id (int): The account ID to retrieve transactions for.
            page (int, optional): The page number for pagination (default is 1).
            limit (int, optional): The number of transactions per page (default is 10).
            recent (bool, optional): Whether to sort by the most recent transactions first (default is True).

        Returns:
            list: A list of Transaction objects for the given account and pagination.
        """
        async with get_session() as session:
            offset = (page - 1) * limit

            # Determine the sorting order based on the 'recent' flag
            order_by_clause = Transaction.transaction_date.desc() if recent else Transaction.transaction_date.asc()

            # Execute the query with filtering, pagination, and sorting
            result = await session.execute(
                select(Transaction)
                .filter(
                    (Transaction.sender_account_id == account_id) |
                    (Transaction.receiver_account_id == account_id)
                )
                .order_by(order_by_clause)
                .offset(offset)
                .limit(limit)
            )
            return result.scalars().all()

    @staticmethod
    async def delete_transaction(transaction_uuid: str):
        """
        Deletes a transaction from the database by its UUID.

        Args:
            transaction_uuid (str): The UUID of the transaction to delete.

        Returns:
            bool: True if the transaction was successfully deleted, otherwise False.
        """
        async with get_session() as session:
            result = await session.execute(select(Transaction).filter(Transaction.uuid == transaction_uuid))
            transaction = result.scalars().first()
            if transaction:
                await session.delete(transaction)
                await session.commit()
                return True
            else:
                return False

    @staticmethod
    async def get_all_transactions(discord_id: int, page: int = 1, limit: int = 10, recent: bool = True):
        """
        Retrieves all transactions for a specific user (either as sender or receiver) with pagination, sorted by date.

        Args:
            discord_id (int): The Discord ID of the user to filter transactions.
            page (int, optional): The page number for pagination (default is 1).
            limit (int, optional): The number of transactions per page (default is 10).
            recent (bool, optional): Whether to sort by the most recent transactions first (default is True).

        Returns:
            list: A list of Transaction objects for the given page and limit.
        """
        async with get_session() as session:
            offset = (page - 1) * limit

            # Determine the sorting order based on the 'recent' flag
            order_by_clause = Transaction.transaction_date.desc() if recent else Transaction.transaction_date.asc()

            # Execute the query to retrieve transactions where the user is either the sender or the receiver
            result = await session.execute(
                select(Transaction)
                .options(selectinload(Transaction.sender), selectinload(Transaction.receiver))  # Eager load the related Account objects
                .where(
                    (Transaction.sender_account_id == discord_id) | (Transaction.receiver_account_id == discord_id)
                )
                .order_by(order_by_clause)
                .offset(offset)
                .limit(limit)
            )
            # Return a list of transaction objects (no need to convert scalars as we are returning the full objects)
            return result.scalars().all()

    @staticmethod
    async def get_total_pages(discord_id: int) -> int:
        """
        Get the total number of transactions for a user.

        Args:
            discord_id (int): The Discord ID of the user.

        Returns:
            int: Total number of transactions.
        """
        async with get_session() as session:
            result = await session.execute(
                select(func.count()).where(
                    (Transaction.sender_account_id == discord_id) | (Transaction.receiver_account_id == discord_id)
                )
            )
            return result.scalar()