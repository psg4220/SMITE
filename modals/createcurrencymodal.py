import discord
from discord import app_commands
from discord.ext import commands
from services.currencyservice import CurrencyService
from services.transactionservice import TransactionService
from services.roleservice import RoleService
from services.accountservice import AccountService


class CreateCurrencyModal(discord.ui.Modal, title="Create a New Currency"):
    name = discord.ui.TextInput(
        label="Currency Name",
        placeholder="Enter the name of your currency",
        max_length=128,
    )
    ticker = discord.ui.TextInput(
        label="Ticker",
        placeholder="Enter a short ticker (e.g., USD)",
        max_length=4,
        min_length=3
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        # Logic for handling currency creation
        currency_name = self.name.value
        ticker = self.ticker.value

        try:
            # Check ticker formatting
            if not ticker.isalpha():
                embed = discord.Embed(
                    title="Invalid Ticker Format",
                    description="Ticker should only contain letters.",
                    color=0xff0000,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            existing_currency_name = await CurrencyService.read_currency_by_name(currency_name)
            existing_currency_ticker = await CurrencyService.read_currency_by_ticker(ticker.upper())

            # Check for existing currencies
            if existing_currency_name:
                embed = discord.Embed(
                    title="Currency Name Already Exists",
                    description="A currency with this name already exists. Please choose another.",
                    color=0xff0000,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if existing_currency_ticker:
                embed = discord.Embed(
                    title="Currency Ticker Already Exists",
                    description="A currency with this ticker already exists. Please choose another.",
                    color=0xff0000,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check if user already owned a currency
            already_executive = await RoleService.is_executive(interaction.user.id)
            if already_executive:
                embed = discord.Embed(
                    title="You are already an EXECUTIVE",
                    description="You have already created a currency or are an executive of one. Only one currency is "
                                "allowed per user.",
                    color=0xff0000,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            # Initiate creation
            created_currency = await CurrencyService.create_currency(currency_name, ticker.upper())

            # Check if currency creation is success
            if not created_currency:
                embed = discord.Embed(title="Failed to create a currency",
                                      description="There's seems to be a problem creating your currency.",
                                      color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await RoleService.create_role(interaction.user.id, created_currency.currency_id, 1)
            await AccountService.create_account(interaction.user.id, created_currency.currency_id)

            embed = discord.Embed(title="Your currency has been created!",
                                  description=f"{currency_name} (${ticker.upper()})\n",
                                  color=0x00ff00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error occurred during currency creation: {e}")

            # User-friendly error message
            embed = discord.Embed(
                title="An Error Occurred!",
                description="Something went wrong. Please contact an administrator.",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
