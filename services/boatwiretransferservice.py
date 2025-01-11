from sqlalchemy.exc import NoResultFound
from models.boatauthlist import BoatAuthList
from db import get_session
from sqlalchemy.future import select


class BoatAuthListService:

    @staticmethod
    async def create_wire_service(guild_id: int, currency_id: int, token: str) -> BoatAuthList:
        """
        Create a new wire service entry for a guild with the provided token.

        :param guild_id: The Discord guild ID.
        :param currency_id: The currency id.
        :param token: The authorization token.
        :return: The created `BoatAuthList` object.
        """
        async with get_session() as session:
            new_entry = BoatAuthList(guild_id=guild_id, token=token, currency_id=currency_id)
            session.add(new_entry)
            await session.commit()
            return new_entry

    @staticmethod
    async def get_token_by_guild_id(guild_id: int) -> BoatAuthList:
        """
        Retrieve the token for a specific guild ID.

        :param guild_id: The Discord guild ID.
        :return: The `BoatAuthList` object containing the token None otherwise.
        """
        async with get_session() as session:
            query = select(BoatAuthList).where(BoatAuthList.guild_id == guild_id)
            result = await session.execute(query)
            boat_auth = result.scalar_one_or_none()
            if not boat_auth:
                return None
            return boat_auth

    @staticmethod
    async def get_token_by_currency_id(currency_id: int) -> BoatAuthList:
        """
        Retrieve the token for a specific guild ID.

        :param currency_id: The currency id.
        :return: The `BoatAuthList` object containing the token None otherwise.
        """
        async with get_session() as session:
            query = select(BoatAuthList).where(BoatAuthList.currency_id == currency_id)
            result = await session.execute(query)
            boat_auth = result.scalar_one_or_none()
            if not boat_auth:
                return None
            return boat_auth

    @staticmethod
    async def set_token(guild_id: int, currency_id: int, token: str) -> BoatAuthList:
        """
        Update the token for a specific guild ID. Creates a new entry if none exists.

        :param guild_id: The Discord guild ID.
        :param currency_id: The currency id.
        :param token: The new authorization token.
        :return: The updated or created `BoatAuthList` object.
        """
        async with get_session() as session:
            query = select(BoatAuthList).where(BoatAuthList.guild_id == guild_id)
            result = await session.execute(query)
            boat_auth = result.scalar_one_or_none()

            if boat_auth:
                boat_auth.token = token
            else:
                boat_auth = BoatAuthList(guild_id=guild_id, token=token, currency_id=currency_id)
                session.add(boat_auth)

            await session.commit()
            return boat_auth

    @staticmethod
    async def delete_token(guild_id: int) -> bool:
        """
        Delete the token for a specific guild ID.

        :param guild_id: The Discord guild ID.
        :return: `True` if deletion was successful, `False` otherwise.
        """
        async with get_session() as session:
            query = select(BoatAuthList).where(BoatAuthList.guild_id == guild_id)
            result = await session.execute(query)
            boat_auth = result.scalar_one_or_none()

            if boat_auth:
                await session.delete(boat_auth)
                await session.commit()
                return True

            return False
