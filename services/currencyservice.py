from models.currency import Currency
from db import get_session
from sqlalchemy.future import select


class CurrencyService:

    @staticmethod
    async def create_currency(name: str, ticker: str, is_disabled: bool = False):
        """
        Creates a new currency entry in the database.

        Args:
            name (str): The name of the currency.
            ticker (str): The ticker symbol of the currency.
            is_disabled (bool, optional): Whether the currency is disabled. Defaults to False.

        Returns:
            Currency: The created Currency object.
        """
        async with get_session() as session:
            new_currency = Currency(name=name, ticker=ticker, is_disabled=is_disabled)
            session.add(new_currency)
            await session.commit()
            await session.refresh(new_currency)
            return new_currency

    @staticmethod
    async def read_currency_by_field(field: str, value):
        """
        Retrieves a currency based on a specified field and value from the database.

        Args:
            field (str): The field to filter by (e.g., 'currency_id', 'name', 'ticker').
            value (Any): The value of the field to search for.

        Returns:
            Currency or None: The Currency object if found, otherwise None.
        """
        async with get_session() as session:
            field_map = {
                "currency_id": Currency.currency_id,
                "name": Currency.name,
                "ticker": Currency.ticker,
            }

            if field not in field_map:
                raise ValueError(f"Invalid field '{field}'. Must be one of: {', '.join(field_map.keys())}")

            result = await session.execute(select(Currency).filter(field_map[field] == value))
            currency = result.scalars().first()
            return currency

    @staticmethod
    async def read_currency_by_id(currency_id: int):
        """
        Retrieves a currency by its ID from the database.

        Args:
            currency_id (int): The ID of the currency to retrieve.

        Returns:
            Currency or None: The Currency object if found, otherwise None.
        """
        return await CurrencyService.read_currency_by_field("currency_id", currency_id)

    @staticmethod
    async def read_currency_by_name(name: str):
        """
        Retrieves a currency by its name from the database.

        Args:
            name (str): The name of the currency to retrieve.

        Returns:
            Currency or None: The Currency object if found, otherwise None.
        """
        return await CurrencyService.read_currency_by_field("name", name)

    @staticmethod
    async def read_currency_by_ticker(ticker: str):
        """
        Retrieves a currency by its ticker from the database.

        Args:
            ticker (str): The ticker of the currency to retrieve.

        Returns:
            Currency or None: The Currency object if found, otherwise None.
        """
        return await CurrencyService.read_currency_by_field("ticker", ticker)

    @staticmethod
    async def update_currency(currency_id: int, new_name: str, new_ticker: str):
        """
        Updates an existing currency in the database by its ID.

        Args:
            currency_id (int): The ID of the currency to update.
            new_name (str): The new name for the currency.
            new_ticker (str): The new ticker for the currency.

        Returns:
            Currency or None: The updated Currency object if found and updated, otherwise None.
        """
        async with get_session() as session:
            result = await session.execute(select(Currency).filter(Currency.currency_id == currency_id))
            currency = result.scalars().first()
            if currency:
                currency.name = new_name
                currency.ticker = new_ticker
                await session.commit()
                return currency
            else:
                return None

    @staticmethod
    async def delete_currency(currency_id: int):
        """
        Deletes a currency from the database by its ID.

        Args:
            currency_id (int): The ID of the currency to delete.

        Returns:
            bool: True if the currency was successfully deleted, otherwise False.
        """
        async with get_session() as session:
            result = await session.execute(select(Currency).filter(Currency.currency_id == currency_id))
            currency = result.scalars().first()
            if currency:
                await session.delete(currency)
                await session.commit()
                return True
            else:
                return False

    @staticmethod
    async def get_all_currencies(page: int = 1, limit: int = 10, is_disabled: bool = False):
        """
        Retrieves all currencies with pagination from the database.

        Args:
            page (int, optional): The page number for pagination (default is 1).
            limit (int, optional): The number of currencies per page (default is 10).
            is_disabled (bool, optional): Whether to include disabled currencies (default is False).

        Returns:
            list: A list of Currency objects for the given page and limit.
        """
        async with get_session() as session:
            offset = (page - 1) * limit  # Calculate the offset based on page and limit

            # Execute the query with pagination and filter by 'is_disabled'
            result = await session.execute(
                select(Currency).filter(Currency.is_disabled == is_disabled)
                .offset(offset).limit(limit)
            )
            return result.scalars().all()

