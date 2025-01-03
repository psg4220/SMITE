from typing import Tuple

import discord
import time
import io
from datetime import timedelta
from discord import app_commands, Embed, File
from discord.ext import commands
from modals.createcurrencymodal import CreateCurrencyModal
from modals.mintmodal import MintModal
from modals.burnmodal import BurnModal
from models.trade import TradeStatus, TradeType
from views.tradelimitview import TradeLimitView, display_trade_info
from views.tradelogview import TradeLogView
from plotting.chartplotter import ChartPlotter
from services.tradelogservice import TradeLogService
from services.currencyservice import CurrencyService
from services.tradeservice import TradeService
from views.activetradeview import ActiveTradeView
from utilities.embedtable import EmbedTable

class TradeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    group = app_commands.Group(name="trade", description="The trade command")

    @group.command(name="limit", description="List your trade at the market")
    async def trade_limit(self, interaction: discord.Interaction, ticker_pair: str) -> None:
        await interaction.response.defer()
        base_ticker, quote_ticker = ticker_pair.split("/")

        # Check if it is the same tickers
        if base_ticker.upper() == quote_ticker.upper():
            embed = discord.Embed(
                title="Same Ticker!",
                description="You cannot put the same ticker",
                color=0xff0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Retrieve base and quote currencies
        base_currency = await CurrencyService.read_currency_by_ticker(base_ticker)
        quote_currency = await CurrencyService.read_currency_by_ticker(quote_ticker)

        # Check if base and quote is not empty
        if not base_currency or not quote_currency:
            embed = discord.Embed(
                title="Invalid Ticker",
                description="The ticker you have entered is invalid or it doesn't exist",
                color=0xff0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Get the last trade log
        last_trade_log = await TradeLogService.get_last_trade_log(
            base_currency.currency_id, quote_currency.currency_id
        )

        # Check if there is a last trade log
        if last_trade_log:
            embed = await display_trade_info(last_trade_log, base_currency, quote_currency)
            view = TradeLimitView(
                bot=self.bot, embed=embed[0], base_currency=base_currency, quote_currency=quote_currency,
                user=interaction.user, chart=embed[1]
            )
            await interaction.followup.send(embed=embed[0], view=view, file=embed[2])
        else:
            embed = await display_trade_info(
                last_trade_log,
                base_currency,
                quote_currency
            )
            view = TradeLimitView(
                bot=self.bot, base_currency=base_currency, quote_currency=quote_currency,
                embed=embed, user=interaction.user
            )
            view.select_chart_type.disabled = True
            view.select_timeframe.disabled = True
            view.refresh_button.disabled = True
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @group.command(name="cancel", description="Cancel your trade")
    async def cancel_trade(self, interaction: discord.Interaction, trade_id: int) -> None:
        await interaction.response.defer(ephemeral=True)
        trade = await TradeService.read_trade_by_id(trade_id)
        if trade.trade_id != trade_id:
            embed = Embed(
                title="TRADE IS NOT YOURS",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
        success = await TradeService.cancel_trade(trade_id)
        if success:
            embed = Embed(
                title="TRADE CANCELED",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = Embed(
                title="FAILED TO CANCEL TRADE",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)

    # @group.command(name="peer", description="P2P trade with someone")
    # async def trade_peer(self, interaction: discord.Interaction, amount: str, receiver_account_number: str = None,):
    #
    #     if not receiver_account_number:
    #         await interaction.response.defer()
    #
    #         button = discord.ui.Button(label="ACCEPT TRADE")
    #         # Define the button callback
    #         async def button_callback(interaction: discord.Interaction):
    #             user_discord_id = await interaction.user.id
    #             result = await TradeService.pee
    #
    #         button.callback = button_callback
    #         # Create a view and add the button to it
    #         view = View()
    #         view.add_item(button)
    #
    #         # Send a message with the button
    #         await interaction.followup.send(
    #             view=view,
    #             ephemeral=True,
    #         )
    #         return
    #
    #         # button here
    #     await interaction.response.defer(ephemeral=True)

    @group.command(name="active", description="View your active trades")
    @app_commands.choices(trade_type=[
        app_commands.Choice(name="BUY", value=0),
        app_commands.Choice(name="SELL", value=1),
    ])
    async def active_trades(self, interaction: discord.Interaction, trade_type: int = None):
        """
        Displays active trades for the user with pagination.
        """
        await interaction.response.defer(ephemeral=False)

        view = ActiveTradeView()
        view.user = interaction.user
        view.trade_type = TradeType.BUY if trade_type == 0 else TradeType.SELL

        # Send initial message with placeholder content
        message = await interaction.followup.send("Loading active trades...", view=view)

        # Link the view to the message and display the first page
        view.message = message
        await view.trade_view(interaction)

    @group.command(name="board", description="View trading pairs")
    async def trade_board(self, interaction: discord.Interaction):
        """
        Allows the user to view paginated trade logs.
        """
        await interaction.response.defer(ephemeral=False)
        # Initialize the view and set the user
        view = TradeLogView()
        view.user = interaction.user

        # Send an initial message
        message = await interaction.followup.send("Fetching trade logs...", view=view)
        view.message = message  # Attach the message to the view

        # Load and display the first page
        await view.trade_log_view(interaction)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TradeCog(bot))

    # Sync the slash commands to Discord
    @bot.event
    async def on_ready():
        # Initialize the start_time when the bot is ready
        bot.start_time = time.time()  # This sets the start_time attribute

        # Syncing the slash commands (if needed)
        await bot.tree.sync()
        print("Slash commands synced!")
