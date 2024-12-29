import discord
from discord import Interaction
from discord.ui import View, Button, Select
from models.trade import TradeStatus, TradeType
from services.currencyservice import CurrencyService
from services.tradeservice import TradeService
from utilities.embedtable import EmbedTable

class ActiveTradeView(View):
    def __init__(self, trade_type: TradeType, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.left_button.disabled = True
        self.page = 1
        self.user = None
        self.total_pages = 0
        self.trade_type = trade_type

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Prevents other users from interacting with this view.
        """
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This interaction is not for you!", ephemeral=True
            )
            return False
        return True

    async def update_buttons(self):
        """
        Update the state of the navigation buttons based on the current page.
        """
        self.children[0].disabled = self.page == 1  # Disable the left button if on the first page
        self.children[1].disabled = self.page == self.total_pages  # Disable the right button if on the last page

    async def trade_view(self, interaction: discord.Interaction):
        """
        Generate and display the table of trades for the current page.
        """
        await interaction.response.defer()

        # Get total pages for the user
        self.total_pages = await TradeService.get_total_pages(
            discord_id=interaction.user.id,
            trade_type=self.trade_type,
            status=TradeStatus.OPEN,
            limit=10  # Number of rows per page
        )

        await self.check_pages()


        # Get the trade list
        trades = await TradeService.get_all_trades(
            discord_id=interaction.user.id,
            trade_type=self.trade_type,
            status=TradeStatus.OPEN,
            page=self.page
        )

        # Convert trade data into a 2D array for the table
        trade_data = [["Trade ID", "Ticker Pair", "Type", "Price", "Quantity"]]
        for trade in trades:
            base_currency = await CurrencyService.read_currency_by_id(trade.base_currency_id)
            quote_currency = await CurrencyService.read_currency_by_id(trade.quote_currency_id)
            trade_data.append(
                [str(trade.trade_id), f"{base_currency.ticker.upper()}/{quote_currency.ticker.upper()}", str(trade.type.value),
                 str(trade.price_offered), str(trade.amount)]
            )

        # Generate the table using EmbedTable
        table = EmbedTable(trade_data)
        table_message = table.generate_table()

        # Update the button states
        await self.update_buttons()

        # Edit the original message with the new table
        await interaction.message.edit(content=table_message, view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.gray, custom_id="left_button")
    async def left_button(self, interaction: discord.Interaction, button: Button):
        self.page -= 1
        await self.trade_view(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.gray, custom_id="right_button")
    async def right_button(self, interaction: discord.Interaction, button: Button):
        self.page += 1
        await self.trade_view(interaction)

    @discord.ui.select(
        placeholder="Select Trade Type",
        options=[
            discord.SelectOption(label="BUY", description="View BUY orders only", value="buy"),
            discord.SelectOption(label="SELL", description="View SELL orders only", value="sell"),
            discord.SelectOption(label="ALL", description="View ALL", value="all")
        ]
    )
    async def select_trade_type(self, interaction: discord.Interaction, select: Select):
        selected_trade_type = select.values[0]
        trade_type = None
        if selected_trade_type == "buy":
            trade_type = TradeType.BUY
        elif selected_trade_type == "sell":
            trade_type = TradeType.SELL

        self.trade_type = trade_type
        await self.trade_view(interaction)


    async def check_pages(self):
        if self.page > self.total_pages:
            self.page = self.total_pages

    async def on_timeout(self):
        """
        Handle what happens when the view times out.
        """
        for item in self.children:
            item.disabled = True  # Disable all components when the view times out
        # Optionally edit the original message to reflect the timeout
        if hasattr(self, "message"):
            await self.message.edit(content="This view has timed out.", view=self)
