import datetime

import discord
import time
from discord import app_commands
from discord.ext import commands

from services.accountservice import AccountService
from utilities.tools import separate_account_number
from services.currencyservice import CurrencyService
from services.roleservice import RoleService

class RoleCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    group = app_commands.Group(name="role", description="The role command")

    @group.command(name="help", description="Guide for roles")
    async def help(self, interaction: discord.Interaction):
        description = '''
        The currency is governed by the EXECUTIVE which is the highest role.
        There can be only 1 EXECUTIVE per currency.
        
        ADMIN has the ability to mint or burn currencies
        
        BE CAREFUL OF SETTING SOMEONE EXECUTIVE THIS IS TECHNICALLY
        A TRANSFER OF OWNERSHIP TO SOMEONE.
        '''

        embed = discord.Embed(
            title="GUIDE FOR SETTING ROLES",
            description=description
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @group.command(name="set", description="Sets role to a user")
    @app_commands.choices(role_type=[
        app_commands.Choice(name="EXECUTIVE", value=1),
        app_commands.Choice(name="ADMIN", value=2),
        app_commands.Choice(name="NONE", value=3)
    ])
    async def set_role(self, interaction: discord.Interaction, account_number: str, role_type: int) -> None:
        await interaction.response.defer(ephemeral=True)
        ticker, discord_id = separate_account_number(account_number)

        currency = await CurrencyService.read_currency_by_ticker(ticker.upper())
        user_role = await RoleService.get_role(interaction.user.id, currency.currency_id)
        is_executive = await RoleService.is_executive(discord_id)

        # Checks if the member totally exists
        member = await AccountService.get_account(discord_id, currency.currency_id)
        if not member:
            embed = discord.Embed(
                title="INVALID ACCOUNT NUMBER",
                description="Make sure that the account number has been created\n"
                            "Please tell the user to create an account",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
            return

        # Verify if user is an executive to this currency
        if user_role.role_number != 1:
            embed = discord.Embed(
                title="INSUFFICIENT PERMISSIONS",
                description="You dont have permissions to do this",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
            return

        # Check if the member is an executive
        if is_executive:
            embed = discord.Embed(
                title="USER IS ALREADY AN EXECUTIVE",
                description="The user has already a currency\n"
                            "or your setting roles to yourself.\n"
                            "If you want to delete your currency contact SMITE discord server",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
            return

        if role_type == 1:
            await RoleService.delete_role(interaction.user.id, currency.currency_id)
            await RoleService.create_role(discord_id, currency.currency_id, 1)
            embed = discord.Embed(
                title="EXECUTIVE ROLE HAS BEEN TRANSFERRED AND IMPLEMENTED",
                description="The ownership of the currency has been transferred",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed)

        elif role_type == 2:
            role = await RoleService.set_role(discord_id, currency.currency_id, role_type)
            if not role:
                await RoleService.create_role(discord_id, currency.currency_id, role_type)

            embed = discord.Embed(
                title="ADMIN ROLE HAS BEEN IMPLEMENTED",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)

        elif role_type == 3:
            result = await RoleService.delete_role(discord_id, currency.currency_id)
            if result:
                embed = discord.Embed(
                    title="USER'S ROLE HAS BEEN NULLIFIED",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="USER OR CURRENCY DOES NOT EXIST",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleCog(bot))

    # Sync the slash commands to Discord
    @bot.event
    async def on_ready():
        # Initialize the start_time when the bot is ready
        bot.start_time = time.time()  # This sets the start_time attribute

        # Syncing the slash commands (if needed)
        await bot.tree.sync()
        datetime.datetime.now()
