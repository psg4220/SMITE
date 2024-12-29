import discord
import time
from discord import app_commands
from discord.ext import commands
from modals.createcurrencymodal import CreateCurrencyModal
from modals.mintmodal import MintModal
from modals.burnmodal import BurnModal

class CurrencyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    group = app_commands.Group(name="currency", description="The currency command")

    @group.command(name="create", description="Creates your new currency (ONE CURRENCY PER DISCORD USER)")
    async def create_currency(self, interaction: discord.Interaction) -> None:
        modal = CreateCurrencyModal(self.bot)
        await interaction.response.send_modal(modal)

    @group.command(name="mint", description="Produces new currency (DONT MINT TOO MUCH AS IT CAN CAUSE INFLATION)")
    async def mint_currency(self, interaction: discord.Interaction):
        modal = MintModal(self.bot)
        await interaction.response.send_modal(modal)

    @group.command(name="burn", description="Burns currency")
    async def burn_currency(self, interaction: discord.Interaction):
        modal = BurnModal(self.bot)
        await interaction.response.send_modal(modal)

    # @group.command(name="info", description="Views the currency's information")
    # async def currency_information(self, interaction: discord.Interaction) -> None:
    #     pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CurrencyCog(bot))

    # Sync the slash commands to Discord
    @bot.event
    async def on_ready():
        # Initialize the start_time when the bot is ready
        bot.start_time = time.time()  # This sets the start_time attribute

        # Syncing the slash commands (if needed)
        await bot.tree.sync()
        print("Slash commands synced!")
