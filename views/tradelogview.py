import discord
from discord.ui import View, Button
from services.tradelogservice import TradeLogService
from utilities.embedtable import EmbedTable

class TradeLogView(View):
    def __init__(self, timeout: float = 180):
        """
        Initializes the TradeLogView for paginated display of trade logs.

        Args:
            timeout (float, optional): Timeout for the view. Defaults to 180.
        """
        super().__init__(timeout=timeout)
        self.page = 1
        self.total_pages = 0
        self.user = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Ensures only the user who initiated the interaction can interact with the view.
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
        self.children[0].disabled = self.page == 1  # Disable left button on the first page
        self.children[1].disabled = self.page == self.total_pages  # Disable right button on the last page

    async def trade_log_view(self, interaction: discord.Interaction):
        """
        Generates and displays the trade log list for the current page.
        """
        # Fetch paginated trade log data
        trade_logs, self.total_pages = await TradeLogService.get_trade_log_list_with_price(page=self.page, limit=10)

        # If no trade logs, show a message
        if not trade_logs:
            table_message = "No trade logs available."
        else:
            # Prepare data for the table
            trade_data = [["Base Ticker", "Quote Ticker", "Recent Price"]]
            for base_ticker, quote_ticker, price in trade_logs:
                trade_data.append([base_ticker, quote_ticker, str(price)])

            # Generate table using EmbedTable utility
            table = EmbedTable(trade_data)
            table_message = table.generate_table()

        # Update navigation buttons
        await self.update_buttons()

        # Edit the original message with the updated content
        if self.message:
            await self.message.edit(content=table_message, view=self)
        else:
            raise ValueError("View message is not set.")

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.gray, custom_id="left_button")
    async def left_button(self, interaction: discord.Interaction, button: Button):
        """
        Navigates to the previous page when the left button is clicked.
        """
        if self.page > 1:
            await interaction.response.defer()
            self.page -= 1
            await self.trade_log_view(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.gray, custom_id="right_button")
    async def right_button(self, interaction: discord.Interaction, button: Button):
        """
        Navigates to the next page when the right button is clicked.
        """
        if self.page < self.total_pages:
            await interaction.response.defer()
            self.page += 1
            await self.trade_log_view(interaction)

    async def on_timeout(self):
        """
        Handles view timeout by disabling all interaction components.
        """
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(content="This view has timed out.", view=self)
