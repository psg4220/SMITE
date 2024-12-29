import discord
from discord.ui import View, Button
from services.transactionservice import TransactionService
from utilities.embedtable import EmbedTable


class TransactionListView(View):
    def __init__(self, timeout: float = 180):
        """
        Initialize the TransactionListView.

        Args:
            timeout (float, optional): The timeout in seconds for the view. Defaults to 180.
        """
        super().__init__(timeout=timeout)
        self.page = 1  # Start at page 1
        self.total_pages = 0  # Total number of pages will be calculated dynamically
        self.user = None  # User associated with the view

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

    async def transaction_view(self, interaction: discord.Interaction):
        """
        Generates and displays a table of transactions for the current page.
        """
        # Get the total number of pages for the user based on the transactions available
        self.total_pages = await TransactionService.get_total_pages(
            discord_id=interaction.user.id
        )

        # Fetch the transactions for the current page
        transactions = await TransactionService.get_all_transactions(
            discord_id=interaction.user.id,
            page=self.page,
            limit=10  # Number of transactions per page
        )

        # If no transactions, show a message stating there are none
        if not transactions:
            print("No transactions")
            table_message = "No transactions available."
        else:
            # Prepare data for the table
            transaction_data = [["Date", "Amount", "Sender", "Receiver"]]
            for transaction in transactions:
                sender_account = transaction.sender  # Assuming sender is an Account object
                receiver_account = transaction.receiver  # Assuming receiver is an Account object

                # Append formatted data to the table
                transaction_data.append([
                    transaction.transaction_date.strftime("%Y-%m-%d %H:%M:%S"),  # Format date
                    str(transaction.amount),  # Transaction amount
                    str(sender_account.discord_id),  # Use sender's Discord ID (or another identifier)
                    str(receiver_account.discord_id),  # Use receiver's Discord ID (or another identifier)
                ])

            # Generate the table using the EmbedTable utility
            table = EmbedTable(transaction_data)
            table_message = table.generate_table()

        # Update the pagination buttons based on the page number
        await self.update_buttons()

        # Edit the original message with the newly generated table or the "No transactions" message
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
            self.page -= 1  # Decrease page number
            await self.transaction_view(interaction)  # Re-render the view with updated data

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.gray, custom_id="right_button")
    async def right_button(self, interaction: discord.Interaction, button: Button):
        """
        Navigate to the next page when the right button is clicked.
        """
        if self.page < self.total_pages:
            self.page += 1  # Increase page number
            await self.transaction_view(interaction)  # Re-render the view with updated data

    async def on_timeout(self):
        """
        Handle what happens when the view times out. Disable all interaction components.
        """
        for item in self.children:
            item.disabled = True  # Disable all buttons after timeout
        if self.message:
            await self.message.edit(content="This view has timed out.", view=self)  # Edit the message to indicate timeout
