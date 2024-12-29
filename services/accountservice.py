from models.account import Account
from models.transaction import Transaction
from db import get_session
from sqlalchemy.future import select
from sqlalchemy import update, func
from decimal import Decimal


class AccountService:

    @staticmethod
    async def create_account(discord_id: int,
                             currency_id: int,
                             balance: Decimal = Decimal(0),
                             is_disabled: bool = False):
        """
        Creates a new account in the database.

        Args:
            discord_id (int): The Discord ID associated with the account.
            currency_id (int): The ID of the currency for this account.
            balance (Decimal, optional): The initial balance for the account. Defaults to 0.0.
            is_disabled (bool, optional): Whether the account is disabled. Defaults to False.

        Returns:
            Account: The created Account object.
        """
        async with get_session() as session:
            new_account = Account(discord_id=discord_id, currency_id=currency_id, balance=balance,
                                  is_disabled=is_disabled)
            session.add(new_account)
            await session.commit()
            await session.refresh(new_account)
            return new_account

    @staticmethod
    async def read_account_by_id(account_id: int):
        """
        Retrieves an account by its ID from the database.

        Args:
            account_id (int): The ID of the account to retrieve.

        Returns:
            Account or None: The Account object if found, otherwise None.
        """
        async with get_session() as session:
            result = await session.execute(select(Account).filter(Account.account_id == account_id))
            account = result.scalars().first()
            return account

    @staticmethod
    async def get_account(discord_id: int, currency_id: int):
        """
        Retrieves an account by its discord_id and currency_id.

        Args:
            discord_id (int): The Discord ID associated with the account.
            currency_id (int): The ID of the currency for the account.

        Returns:
            Account or None: The Account object if found, otherwise None.
        """
        async with get_session() as session:
            # Execute query to find the account by discord_id and currency_id
            result = await session.execute(
                select(Account).filter_by(discord_id=discord_id, currency_id=currency_id)
            )
            account = result.scalars().first()

            if account:
                return account
            else:
                return None

    @staticmethod
    async def update_account_balance(account_id: int, new_balance: Decimal):
        """
        Updates the balance of an account by its ID.

        Args:
            account_id (int): The ID of the account to update.
            new_balance (Decimal): The new balance for the account.

        Returns:
            Account or None: The updated Account object if found and updated, otherwise None.
        """
        async with get_session() as session:
            result = await session.execute(select(Account).filter(Account.account_id == account_id))
            account = result.scalars().first()
            if account:
                account.balance = new_balance
                await session.commit()
                return account
            else:
                return None

    @staticmethod
    async def disable(account_id: int, is_disabled: bool):
        """
        Sets the is_disabled status of an account by its account_id.

        Args:
            account_id (int): The ID of the account to disable/enable.
            is_disabled (bool): The status to set (True to disable, False to enable).

        Returns:
            bool: True if the account's status was updated, False if the account was not found.
        """
        async with get_session() as session:
            # Find the account by account_id
            result = await session.execute(
                select(Account).filter_by(account_id=account_id)
            )
            account = result.scalars().first()

            if not account:
                return False

            # Update the is_disabled status
            account.is_disabled = is_disabled
            await session.commit()
            return True

    @staticmethod
    async def is_disabled(account_id: int):
        """
        Gets the is_disabled status of an account by its account_id.

        Args:
            account_id (int): The ID of the account.
        Returns:
            bool: True if its disabled false otherwise.
        """
        async with get_session() as session:
            # Find the account by account_id
            result = await session.execute(
                select(Account).filter_by(account_id=account_id)
            )
            account = result.scalars().first()

            return account.is_disabled

    @staticmethod
    async def delete_account(account_id: int):
        """
        Deletes an account from the database by its ID.

        Args:
            account_id (int): The ID of the account to delete.

        Returns:
            bool: True if the account was successfully deleted, otherwise False.
        """
        async with get_session() as session:
            result = await session.execute(select(Account).filter(Account.account_id == account_id))
            account = result.scalars().first()
            if account:
                await session.delete(account)
                await session.commit()
                return True
            else:
                return False

    @staticmethod
    async def get_all_accounts(page: int = 1, limit: int = 10, is_disabled: bool = False):
        """
        Retrieves all accounts with pagination from the database.

        Args:
            page (int, optional): The page number for pagination (default is 1).
            limit (int, optional): The number of accounts per page (default is 10).
            is_disabled (bool, optional): Whether to include disabled accounts (default is False).

        Returns:
            list: A list of Account objects for the given page and limit.
        """
        async with get_session() as session:
            offset = (page - 1) * limit  # Calculate the offset based on page and limit

            # Execute the query with pagination and filter by 'is_disabled'
            result = await session.execute(
                select(Account).filter(Account.is_disabled == is_disabled)
                .offset(offset).limit(limit)
            )
            return result.scalars().all()

    @staticmethod
    async def transfer(sender_discord_id: int, receiver_discord_id: int, currency_id: int, amount: Decimal):
        """
        Transfers a specified amount of currency from the sender's account to the receiver's account.

        Args:
            sender_discord_id (int): The Discord ID of the user sending the currency.
            receiver_discord_id (int): The Discord ID of the user receiving the currency.
            currency_id (int): The ID of the currency being transferred.
            amount (Decimal): The amount of currency to transfer.

        Returns:
            Transaction (Transaction): The transaction record of the completed transfer if successful.
            int: Error codes indicating specific issues during the transfer:
                -1: Transfer amount is zero or negative.
                -2: Sender's account does not exist for the specified currency.
                -3: Sender and receiver accounts are the same.
                -4: Insufficient balance in the sender's account.

        Behavior:
            - If the sender or receiver account doesn't exist, an appropriate error code is returned.
            - If the receiver's account doesn't exist, it will be created automatically.
            - Transfers with zero or negative amounts are rejected.
            - Atomic updates are performed on sender's and receiver's balances.
        """
        # Check if amount is zero or negative
        if amount <= Decimal('0.00'):
            return -1

        async with get_session() as session:
            # Find sender and receiver accounts
            sender = await AccountService.get_account(sender_discord_id, currency_id)
            receiver = await AccountService.get_account(receiver_discord_id, currency_id)

            # Check if accounts exists
            if not sender:
                return -2
            if not receiver:
                return -5

            if sender.is_disabled or receiver.is_disabled:
                return -6

            # Check if sender is trying to transfer to the same account
            if sender.account_id == receiver.account_id:
                return -3
            # Check if sender has sufficient funds
            if sender.balance < amount:
                return -4

            # Create a new transaction record
            transaction = Transaction(
                sender_account_id=sender.account_id,
                receiver_account_id=receiver.account_id,
                amount=amount
            )
            session.add(transaction)

            # Update the sender's and receiver's balances atomically
            await session.execute(
                update(Account).where(Account.account_id == sender.account_id)
                .values(balance=func.coalesce(Account.balance, 0) - amount)
            )
            await session.execute(
                update(Account).where(Account.account_id == receiver.account_id)
                .values(balance=func.coalesce(Account.balance, 0) + amount)
            )
    
            # Commit the transaction and the balance updates
            await session.commit()
            return transaction
