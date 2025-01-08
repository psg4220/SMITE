import datetime

import discord
import time
from discord import app_commands
from discord.ext import commands
from modals.createcurrencymodal import CreateCurrencyModal
from modals.editcurrencymodal import EditCurrencyModal
from modals.mintmodal import MintModal
from modals.burnmodal import BurnModal
from views.currencylistview import CurrencyListView
class CurrencyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    group = app_commands.Group(name="currency", description="The currency command")

    @group.command(name="help", description="Guide for currency command")
    async def help(self, interaction: discord.Interaction) -> None:
        description = """
        COMMANDS:
        
        **/currency create**
        This creates your currency. It will automatically creates you an account.
        There can be only ONE CURRENCY PER DISCORD USER. (Check /role help for why is that)
        
        **NOTE:**
        **If you mistakenly created a currency and wanted to delete it please go to SMITE server and ask psg420.**
        
        **/currency edit**
        Edits your currency's name and ticker. You must be an EXECUTIVE to do this action.
        
        **/currency mint**
        It produces new money into your account. You must be an EXECUTIVE or an ADMIN to do this action
        Be careful with this command as it can result in inflation (search zimbabwe dollars)
        
        **/currency burn**
        It removes money into your account. You must be an EXECUTIVE or an ADMIN to do this action
        
        **/currency list**
        List of all existing micronational currencies that have been created in SMITE.
        """
        embed = discord.Embed(
            title="GUIDE FOR CURRENCY COMMANDS",
            description=description
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

    @group.command(name="edit", description="Edits the currency name and or ticker")
    async def currency_edit(self, interaction: discord.Interaction):
        modal = EditCurrencyModal(self.bot)
        await interaction.response.send_modal(modal)

    @group.command(name="list", description="List all the currencies")
    async def currency_list(self, interaction: discord.Interaction) -> None:
        """
        Allows the user to view currencies with pagination.
        """
        await interaction.response.defer(ephemeral=False)
        # Initialize the CurrencyListView
        view = CurrencyListView(is_disabled=False)  # Change `is_disabled` as needed
        view.user = interaction.user  # Set the user for interaction checks

        # Send an initial message and attach the view
        message = await interaction.followup.send("Fetching currencies...", view=view)

        # Attach the message to the view for timeout handling
        view.message = message

        # Load and display the first page of currencies
        await view.currency_view(interaction)

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
        print(datetime.datetime.now())
