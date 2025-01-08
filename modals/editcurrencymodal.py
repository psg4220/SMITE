import discord
from discord import app_commands
from discord.ext import commands
from services.currencyservice import CurrencyService
from services.roleservice import RoleService


class EditCurrencyModal(discord.ui.Modal, title="Edits a currency"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

        self.old_ticker = discord.ui.TextInput(
            label="Current Ticker",
            placeholder="Enter the currency's ticker you want to change",
            max_length=4,
            min_length=3
        )

        self.name = discord.ui.TextInput(
            label="New Currency Name",
            placeholder="(Enter 'none' to leave unchanged)",
            default="none",
            max_length=128,
        )
        self.ticker = discord.ui.TextInput(
            label="New Ticker",
            placeholder="(Enter 'none' to leave unchanged)",
            default="none",
            max_length=4,
            min_length=3,
        )

        self.add_item(self.old_ticker)
        self.add_item(self.name)
        self.add_item(self.ticker)


    async def on_submit(self, interaction: discord.Interaction):
        # Logic for handling currency creation
        old_ticker = self.old_ticker.value
        currency_name = self.name.value
        ticker = self.ticker.value

        try:
            # Check ticker formatting
            if not old_ticker.isalpha() or not ticker.isalpha():
                embed = discord.Embed(
                    title="Invalid Ticker Format",
                    description="Ticker should only contain letters.",
                    color=0xff0000,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            currency = await CurrencyService.read_currency_by_ticker(old_ticker)

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
            is_executive = await RoleService.is_executive(interaction.user.id)
            if is_executive:
                if is_executive.currency_id == currency.currency_id:
                    updated_currency = await CurrencyService.update_currency(
                        currency.currency_id,
                        currency_name if currency_name.lower() != 'none' else currency.name,
                        ticker if ticker.lower() != 'none' else currency.ticker
                    )

                    if updated_currency:
                        embed = discord.Embed(
                            title="The currency has been edited",
                            description=f"Currency Name: {updated_currency.name}\n"
                                        f"Currency Ticker: {updated_currency.ticker}",
                            color=0x00ff00
                        )
                    else:
                        embed = discord.Embed(
                            title="The currency has not been edited",
                            description=f"Please try again later",
                            color=0xff0000
                        )

                    await interaction.response.send_message(embed=embed, ephemeral=True)
            embed = discord.Embed(
                title="Insufficient Permission",
                description="You must be an **EXECUTIVE** to do this",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error occurred during currency editing: {e}")

            # User-friendly error message
            embed = discord.Embed(
                title="An Error Occurred!",
                description="Something went wrong. Please contact an administrator.",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
