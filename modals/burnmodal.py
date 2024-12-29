import discord
from decimal import Decimal
from discord import app_commands
from discord.ext import commands
from utilities.tools import separate_account_number,  validate_decimal
from services.accountservice import AccountService
from services.currencyservice import CurrencyService
from services.roleservice import RoleService

class BurnModal(discord.ui.Modal, title="Burn currency"):
    ticker = discord.ui.TextInput(
        label="Currency ticker",
        placeholder="Enter a currency ticker",
        max_length=4,
        min_length=3
    )
    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="Amount to be minted",
        max_length=18
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        ticker = self.ticker.value
        amount = self.amount.value

        # Retrieve currency and role
        currency = await CurrencyService.read_currency_by_ticker(ticker.upper())
        role = await RoleService.get_role(interaction.user.id, currency.currency_id)

        # If there is no role that means it's a normal user
        if not role:
            embed = discord.Embed(
                title="You're not an ADMIN or EXECUTIVE",
                description="You have NO RIGHT to mint this currency",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not role.role_number in (1, 2) or not role:
            embed = discord.Embed(
                title="You're not an ADMIN or EXECUTIVE",
                description="You have **NO RIGHT** to mint this currency",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        account = await AccountService.get_account(interaction.user.id, currency.currency_id)

        if not account:
            embed = discord.Embed(
                title="No Account",
                description="Your account was not found\n"
                            "Please create an account",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        new_balance = account.balance - Decimal(amount)

        if new_balance < 0:
            await AccountService.update_account_balance(account.account_id, Decimal("0"))
            embed = discord.Embed(
                title="BURNING SUCCESS",
                description=f"You have burnt **{amount}** **{ticker.upper()}**\n"
                            f"Current balance is **0** **{ticker.upper()}**",
                color=0x00ff00,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not validate_decimal(new_balance):
            embed = discord.Embed(
                title="Invalid amount format",
                description="Make sure the amount is not more than 999,999,999,999,999.99\n"
                            "or less than 0.01 or contains any letters, symbols",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        updated_account = await AccountService.update_account_balance(account.account_id, new_balance)

        embed = discord.Embed(
            title="BURNING SUCCESS",
            description=f"You have burnt **{amount}** **{ticker.upper()}**\n"
                        f"Current balance is **{updated_account.balance}** **{ticker.upper()}**",
            color=0x00ff00,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)