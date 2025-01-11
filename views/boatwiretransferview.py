import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import Interaction
from modals.boatconnectmodal import BoatConnectModal
from modals.boatwiretransfermodal import BoatWireTransferModal


class BoatWireTransferView(View):
    def __init__(self, bot: commands.Bot, user: discord.User, timeout: float = 180):
        """
        Initialize the custom view for wire transfers.

        :param bot: The bot instance.
        :param user: The user interacting with the view.
        :param timeout: Time before the view times out (in seconds).
        """
        super().__init__(timeout=timeout)
        self.bot = bot
        self.user = user
        self.embed = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Ensure only the user who initiated the view can interact with it.
        """
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This interaction is not for you!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Transfer In", style=discord.ButtonStyle.green, custom_id="transfer_in", emoji="➕")
    async def transfer_in(self, interaction: Interaction, button: Button):
        modal = BoatWireTransferModal(self.bot, button.custom_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Transfer Out", style=discord.ButtonStyle.red, custom_id="transfer_out", emoji="➖")
    async def transfer_out(self, interaction: Interaction, button: Button):
        modal = BoatWireTransferModal(self.bot, button.custom_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Connect", style=discord.ButtonStyle.secondary, custom_id="connect", emoji="🔗")
    async def connect(self, interaction: Interaction, button: Button):
        modal = BoatConnectModal(self.bot)
        await interaction.response.send_modal(modal)

    @classmethod
    async def display(cls, bot: commands.Bot, interaction: Interaction):
        """
        Create and display the wire transfer embed and view.

        :param bot: The bot instance.
        :param interaction: The interaction that triggered the view.
        """
        await interaction.response.defer()
        embed = discord.Embed(
            title="Wire Transfer",
            description=(
                "You are about to transfer funds from a\n"
                "third-party currency bot to **SMITE**.\n\n"
                "If your the currency and server owner and want to integrate a currency bot to SMITE, click **Connect**"
            ),
            color=0x0000FF,
        )
        view = cls(bot=bot, user=interaction.user)
        view.embed = embed
        await interaction.followup.send(embed=embed, view=view)

    async def on_timeout(self):
        """
        Handles timeout by disabling all buttons and editing the message.
        """
        for item in self.children:
            item.disabled = True
        if self.embed:
            self.embed.set_footer(text="This view has timed out.")
            await self.message.edit(embed=self.embed, view=self)

