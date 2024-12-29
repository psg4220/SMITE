import discord
from decimal import Decimal
from discord import app_commands
from discord.ext import commands

from services.accountservice import AccountService
from services.currencyservice import CurrencyService


class CreateAccountModal(discord.ui.Modal, title="Create an account"):
    ticker = discord.ui.TextInput(
        label="Currency Ticker",
        placeholder="Enter the currency ticker (ex. USD, EUR)",
        max_length=4,
        min_length=3
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        ticker = self.ticker.value
        currency = await CurrencyService.read_currency_by_ticker(ticker.upper())
        existing_account = await AccountService.get_account(interaction.user.id, currency.currency_id)
        if existing_account:
            embed = discord.Embed(
                title="You already have a account for this currency.",
                description="You can only create one account per currency.",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        account = await AccountService.create_account(interaction.user.id, currency.currency_id)

        if account:
            embed = discord.Embed(
                title="ACCOUNT CREATION SUCCESS",
                description=f"Account number: `{ticker.upper()}-{interaction.user.id}`",
                color=0x00ff00,
            )
        else:
            embed = discord.Embed(
                title="ACCOUNT CREATION FAIL",
                description=f"Please try again",
                color=0x00ff00,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
