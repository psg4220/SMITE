import discord
import time
from discord import app_commands
from discord.ext import commands
from services.transactionservice import TransactionService
from views.transactionlistview import TransactionListView


class TransactionCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    group = app_commands.Group(name="transaction", description="The transaction command")

    @group.command(name="list", description="View all of your transactions")
    async def transaction_list(self, interaction: discord.Interaction) -> None:
        """
        Allows the user to view their transactions with pagination.
        """
        await interaction.response.defer(ephemeral=False)
        # Initialize the TransactionListView
        view = TransactionListView()
        view.user = interaction.user  # Set the user for interaction checks

        # Send an initial message and attach the view
        message = await interaction.followup.send("Fetching your transactions...", view=view)

        # Attach the message to the view for timeout handling
        view.message = message

        # Load and display the first page of transactions
        await view.transaction_view(interaction)


    # @group.command(name="info", description="Views the currency's information")
    # async def currency_information(self, interaction: discord.Interaction) -> None:
    #     pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TransactionCog(bot))

    # Sync the slash commands to Discord
    @bot.event
    async def on_ready():
        # Initialize the start_time when the bot is ready
        bot.start_time = time.time()  # This sets the start_time attribute

        # Syncing the slash commands (if needed)
        await bot.tree.sync()
        print("Slash commands synced!")