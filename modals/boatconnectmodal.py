import discord
from decimal import Decimal
from discord import app_commands
from discord.ext import commands
from utilities.tools import separate_account_number, validate_decimal
from services.accountservice import AccountService
from services.currencyservice import CurrencyService
from services.roleservice import RoleService
from services.boatwiretransferservice import BoatAuthListService
from wrapper.unbelievaboat.boatclient import BoatClient


class BoatConnectModal(discord.ui.Modal, title="Connect your modal"):
    ticker = discord.ui.TextInput(
        label="SMITE Currency ticker",
        placeholder="Enter your currency ticker",
        max_length=4,
        min_length=3
    )
    boat_token = discord.ui.TextInput(
        label="UnbelievaBoat token",
        placeholder="Auth token for UnbelievaBoat",
        max_length=255
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ticker = self.ticker.value
        boat_token = self.boat_token.value.strip()

        currency = await CurrencyService.read_currency_by_ticker(ticker)

        # Check if the currency exists
        if not currency:
            embed = discord.Embed(
                title="FAILED TO CONNECT",
                description="The currency doesn't exist",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
            return

        # Gets the role of the user
        role = await RoleService.is_executive(interaction.user.id)

        # Check if your are an executive.
        if not role:
            embed = discord.Embed(
                title="FAILED TO CONNECT",
                description="You are NOT an executive for this currency.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Checks if you are the executive of the currency
        if not role.currency_id == currency.currency_id:
            embed = discord.Embed(
                title="FAILED TO CONNECT",
                description="You are NOT an executive for this currency",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return


        guild_id = interaction.guild_id

        response = await BoatClient.get_balance(guild_id, interaction.user.id, boat_token)

        if len(response) == 1:
            embed = discord.Embed(
                title="AN ERROR OCCURRED",
                description="Make sure it is the right authorization token!",
                color=0xff0000
            )
            print(boat_token)
            await interaction.followup.send(embed=embed)
            return

        auth = await BoatAuthListService.set_token(guild_id=guild_id, currency_id=currency.currency_id, token=boat_token)
        print(auth.boat_id)
        if auth:
            embed = discord.Embed(
                title="CONNECTED",
                description="SMITE is now connected to UnbelievaBoat\n"
                            "**Your balances in UnbelievaBoat**\n"
                            f"Cash: {response['cash']}\n"
                            f"Bank: {response['bank']}\n"
                            f"Total: {response['total']}",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed)
            return
