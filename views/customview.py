import discord
from discord.ui import View, Button, Select


class CustomView(View):
    def __init__(self, timeout: float = 180):
        """
        Initialize the custom view.

        :param timeout: How long the view will listen for interactions (in seconds).
        """
        super().__init__(timeout=timeout)

        # Add default components here if needed
        self.add_item(Button(label="Default Button", style=discord.ButtonStyle.primary, custom_id="default_button"))

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

    @discord.ui.button(label="Click Me!", style=discord.ButtonStyle.green, custom_id="click_me")
    async def click_me_button(self, interaction: discord.Interaction, button: Button):
        """
        Handles the interaction when the "Click Me!" button is pressed.
        """
        await interaction.response.send_message("You clicked the button!", ephemeral=True)

    @discord.ui.select(
        placeholder="Choose an option...",
        options=[
            discord.SelectOption(label="Option 1", description="This is the first option", value="1"),
            discord.SelectOption(label="Option 2", description="This is the second option", value="2"),
        ],
    )
    async def select_menu(self, interaction: discord.Interaction, select: Select):
        """
        Handles the interaction when an option is selected.
        """
        await interaction.response.send_message(f"You selected: {select.values[0]}", ephemeral=True)

    async def on_timeout(self):
        """
        Handle what happens when the view times out.
        """
        for item in self.children:
            item.disabled = True  # Disable all components when the view times out
        # Optionally edit the original message to reflect the timeout
        # This assumes you have access to the message that contains this view
        # await self.message.edit(content="This view has timed out.", view=self)

