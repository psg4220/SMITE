import discord
from typing import Callable, Optional


class Pagination(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, get_page: Callable):
        """
        Initialize the pagination view.

        :param interaction: The original interaction that triggered the pagination.
        :param get_page: A callable that fetches the embed and total pages for the current index.
        """
        super().__init__(timeout=100)
        self.interaction = interaction
        self.get_page = get_page
        self.total_pages: Optional[int] = None
        self.current_page = 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Restrict button interactions to the original command author.
        """
        if interaction.user == self.interaction.user:
            return True
        embed = discord.Embed(
            description="Only the author of the command can perform this action.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    async def start(self):
        """
        Send the initial page and setup pagination.
        """
        embed, self.total_pages = await self.get_page(self.current_page)

        if self.total_pages == 1:
            # Send a message without buttons if there's only one page
            await self.interaction.response.send_message(embed=embed)
        else:
            # Update buttons and send the paginated message
            self.update_buttons()
            await self.interaction.response.send_message(embed=embed, view=self)

    async def update_page(self, interaction: discord.Interaction):
        """
        Update the current page's embed and buttons.
        """
        embed, self.total_pages = await self.get_page(self.current_page)
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    def update_buttons(self):
        """
        Enable or disable buttons based on the current page.
        """
        self.previous_button.disabled = self.current_page == 1
        self.next_button.disabled = self.current_page == self.total_pages
        self.jump_button.label = "Go to Start" if self.current_page > self.total_pages // 2 else "Go to End"

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def previous_button(self, interaction: discord.Interaction, button: discord.Button):
        """
        Navigate to the previous page.
        """
        self.current_page -= 1
        await self.update_page(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.Button):
        """
        Navigate to the next page.
        """
        self.current_page += 1
        await self.update_page(interaction)

    @discord.ui.button(label="Go to End", style=discord.ButtonStyle.blurple)
    async def jump_button(self, interaction: discord.Interaction, button: discord.Button):
        """
        Jump to the start or end of the pages.
        """
        if self.current_page <= self.total_pages // 2:
            self.current_page = self.total_pages
        else:
            self.current_page = 1
        await self.update_page(interaction)

    async def on_timeout(self):
        """
        Handle timeout by disabling buttons and updating the message.
        """
        for item in self.children:
            item.disabled = True
        try:
            message = await self.interaction.original_response()
            await message.edit(view=self)
        except discord.NotFound:
            # Handle case where the message was deleted
            pass

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        """
        Compute the total number of pages based on the total results and results per page.

        :param total_results: Total number of results.
        :param results_per_page: Number of results per page.
        :return: Total number of pages.
        """
        return (total_results + results_per_page - 1) // results_per_page
