import discord
from discord.ui import View, Button, Select
from services.currencyservice import CurrencyService
from utilities.embedtable import EmbedTable

class CurrencyListView(View):
    def __init__(self, is_disabled: bool = False, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.page = 1  # Start at page 1
        self.total_pages = 0  # Total number of pages will be calculated dynamically
        self.is_disabled = is_disabled  # Whether we are including disabled currencies
        self.user = None  # User associated with the view
        self.sort_order = "oldest"  # Default sorting is by oldest

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
        Updates the navigation buttons based on the current page.
        Disables the left button on the first page and the right button on the last page.
        """
        self.children[0].disabled = self.page == 1  # Disable the left button if on the first page
        self.children[1].disabled = self.page == self.total_pages  # Disable the right button if on the last page

    async def currency_view(self, interaction: discord.Interaction):
        """
        Generates and displays a table of currencies for the current page.
        """

        # Get the total number of pages for the user based on the currencies available
        currencies, self.total_pages = await CurrencyService.get_all_currencies(
            page=self.page, limit=10, is_disabled=self.is_disabled, sort_order=self.sort_order
        )

        # If no currencies, show a message stating there are none
        if not currencies:
            table_message = "No currencies available."
        else:
            # Prepare data for the table
            currency_data = [["Currency Ticker", "Currency Name"]]
            for currency in currencies:
                currency_data.append([currency.ticker, currency.name])

            # Generate the table using the EmbedTable utility
            table = EmbedTable(currency_data)
            table_message = table.generate_table()

        # Update the pagination buttons based on the page number
        await self.update_buttons()

        # Edit the original message with the newly generated table or the "No currencies" message
        if self.message:  # Ensure the message exists before editing
            await self.message.edit(content=table_message, view=self)
        else:
            raise ValueError("View message is not set.")

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.gray, custom_id="left_button")
    async def left_button(self, interaction: discord.Interaction, button: Button):
        """
        Navigate to the previous page when the left button is clicked.
        """
        if self.page > 1:
            # Defer the response to prevent timeout errors
            await interaction.response.defer()
            self.page -= 1  # Decrease page number
            await self.currency_view(interaction)  # Re-render the view with updated data

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.gray, custom_id="right_button")
    async def right_button(self, interaction: discord.Interaction, button: Button):
        """
        Navigate to the next page when the right button is clicked.
        """
        if self.page < self.total_pages:
            # Defer the response to prevent timeout errors
            await interaction.response.defer()
            self.page += 1  # Increase page number
            await self.currency_view(interaction)  # Re-render the view with updated data

    @discord.ui.select(
        placeholder="Sort by",
        options=[
            discord.SelectOption(label="Oldest", value="oldest"),
            discord.SelectOption(label="Newest", value="newest"),
        ]
    )
    async def sort_dropdown(self, interaction: discord.Interaction, select: Select):
        """
        Allows the user to select the sorting order for currencies.
        """
        await interaction.response.defer()
        self.sort_order = select.values[0]  # Update the sort order based on the user's selection
        self.page = 1
        await self.currency_view(interaction)  # Re-render the view with the new sort order

    async def on_timeout(self):
        """
        Handle what happens when the view times out. Disable all interaction components.
        """
        for item in self.children:
            item.disabled = True  # Disable all buttons after timeout
        if self.message:
            await self.message.edit(content="This view has timed out.", view=self)  # Edit the message to indicate timeout
