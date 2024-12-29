from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from models import Role
from db import get_session
import enum

class RoleType(enum.Enum):
    EXECUTIVE = 1
    ADMIN = 2

class RoleService:

    @staticmethod
    async def create_role(discord_id, currency_id, role_number):
        """
        Creates a new role.

        :param discord_id: The Discord ID associated with the role.
        :param currency_id: The ID of the currency associated with the role.
        :param role_number: The role number.
        :return: The created Role instance.
        """
        async with get_session() as session:
            new_role = Role(
                discord_id=discord_id,
                currency_id=currency_id,
                role_number=role_number,
            )
            session.add(new_role)
            await session.commit()
            return new_role

    @staticmethod
    async def get_role(discord_id, currency_id):
        """
        Retrieves a role based on Discord ID and Currency ID.

        :param discord_id: The Discord ID associated with the role.
        :param currency_id: The ID of the currency associated with the role.
        :return: The Role instance, or None if not found.
        """
        async with get_session() as session:
            stmt = select(Role).where(
                Role.discord_id == discord_id, Role.currency_id == currency_id
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    @staticmethod
    async def is_executive(discord_id: int) -> Role:
        """
        Checks if the user with the given Discord ID has the role of 'Executive'.

        :param discord_id: The Discord ID of the user.
        :return: The Role object if the user has the 'Executive' role, otherwise None.
        """
        async with get_session() as session:
            stmt = select(Role).where(
                Role.discord_id == discord_id, Role.role_number == 1
            )
            result = await session.execute(stmt)
            role = result.scalars().first()
            return role

    @staticmethod
    async def set_role(discord_id, currency_id, role_number):
        """
        Updates the role number for a specific Discord ID and Currency ID.

        :param discord_id: The Discord ID associated with the role.
        :param currency_id: The ID of the currency associated with the role.
        :param role_number: The new role number to set.
        :return: The updated Role instance, or None if not found.
        """
        async with get_session() as session:
            stmt = select(Role).where(
                Role.discord_id == discord_id, Role.currency_id == currency_id
            )
            result = await session.execute(stmt)
            role = result.scalars().first()

            if role:
                role.role_number = role_number
                await session.commit()
                return role
            return None

    @staticmethod
    async def delete_role(discord_id, currency_id):
        """
        Deletes a role based on Discord ID and Currency ID.

        :param discord_id: The Discord ID associated with the role.
        :param currency_id: The ID of the currency associated with the role.
        :return: True if the role was deleted, False if not found.
        """
        async with get_session() as session:
            stmt = select(Role).where(
                Role.discord_id == discord_id, Role.currency_id == currency_id
            )
            result = await session.execute(stmt)
            role = result.scalars().first()

            if role:
                await session.delete(role)
                await session.commit()
                return True
            return False
