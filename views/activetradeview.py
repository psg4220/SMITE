import discord
from discord import Interaction
from discord.ui import View, Button, Select
from models.trade import TradeStatus, TradeType
from services.currencyservice import CurrencyService
from services.tradeservice import TradeService
from utilities.embedtable import EmbedTable


class ActiveTradeView(View):
    def __init__(self, timeout: float = 180):
        """
        Initialize the ActiveTradeView.

        Args:
            timeout (float): The timeout in seconds for the view.
        """
        super().__init__(timeout=timeout)
        self.page = 1
        self.total_pages = 0
        self.user = None
        self.trade_type = None
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Ensures that only the user who initiated the interaction can interact with the view.
        """
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This interaction is not for you!", ephemeral=True
            )
            return False
        return True

    async def update_buttons(self):
        """
        Updates the state of navigation buttons based on the current page.
        """
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "left_button":
                    child.disabled = self.page == 1
                elif child.custom_id == "right_button":
                    child.disabled = self.page == self.total_pages

    async def trade_view(self, interaction: discord.Interaction):
        """
        Generates and displays a table of trades for the current page.
        """
        # Get total pages for the user
        self.total_pages = await TradeService.get_total_pages(
            discord_id=self.user.id,
            trade_type=self.trade_type,
            status=TradeStatus.OPEN,
            limit=10
        )
        # Adjust page if it exceeds total pages
        if self.page > self.total_pages:
            self.page = self.total_pages

        # Fetch trades for the current page UNNECESSARY REMOVE THIS IN THE FUTURE
        trades = await TradeService.get_all_trades(
            discord_id=self.user.id,
            trade_type=self.trade_type,
            status=TradeStatus.OPEN,
            page=self.page,
            limit=10
        )

        # Prepare data for the table
        trade_data = [["Trade ID", "Ticker Pair", "Type", "Price", "Quantity"]]
        for trade in trades:
            base_currency = await CurrencyService.read_currency_by_id(trade.base_currency_id)
            quote_currency = await CurrencyService.read_currency_by_id(trade.quote_currency_id)
            trade_data.append([
                str(trade.trade_id),
                f"{base_currency.ticker.upper()}/{quote_currency.ticker.upper()}",
                str(trade.type.value),
                str(trade.price_offered),
                str(trade.amount)
            ])

        # Generate table or fallback message
        table_message = (
            EmbedTable(trade_data).generate_table() if trades else "No active trades available."
        )

        # Update buttons and edit the message
        await self.update_buttons()
        if self.message:
            await self.message.edit(content=table_message, view=self)
        else:
            raise ValueError("View message is not set.")

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.gray, custom_id="left_button")
    async def left_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 1:
            await interaction.response.defer()
            self.page -= 1
            await self.trade_view(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.gray, custom_id="right_button")
    async def right_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.total_pages:
            await interaction.response.defer()
            self.page += 1
            await self.trade_view(interaction)

    @discord.ui.select(
        placeholder="Select Trade Type",
        options=[
            discord.SelectOption(label="BUY", description="View BUY orders only", value="buy"),
            discord.SelectOption(label="SELL", description="View SELL orders only", value="sell"),
            discord.SelectOption(label="ALL", description="View ALL trades", value="all")
        ]
    )
    async def select_trade_type(self, interaction: discord.Interaction, select: Select):
        selected_trade_type = select.values[0]
        self.trade_type = {
            "buy": TradeType.BUY,
            "sell": TradeType.SELL
        }.get(selected_trade_type, None)
        await interaction.response.defer()
        self.page = 1  # Reset to the first page
        await self.trade_view(interaction)

    async def on_timeout(self):
        """
        Handles timeout by disabling all buttons and editing the message.
        """
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(content="This view has timed out.", view=self)

