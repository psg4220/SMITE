import datetime
import discord
from discord.app_commands import describe
from discord.ext import commands
from discord import app_commands
from views.boatwiretransferview import BoatWireTransferView
import time

class WireTransfer(commands.GroupCog, group_name="wire"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Guide for wire transfers")
    async def help(self, interaction: discord.Interaction):
        description = """
        
        """
        embed = discord.Embed(
            title="GUIDE FOR WIRE TRANSFER",
            description=description,
            color=0x808080
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="transfer", description="Wire transfer to a third party bot")
    async def transfer(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.DMChannel):
            embed = discord.Embed(
                title="Invalid Channel",
                description="Please run this on the discord server that has the currency bot",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await BoatWireTransferView.display(self.bot, interaction)



async def setup(bot):
    await bot.add_cog(WireTransfer(bot))  # Await the add_cog() method

    # Sync the slash commands to Discord
    @bot.event
    async def on_ready():
        # Initialize the start_time when the bot is ready
        bot.start_time = time.time()  # This sets the start_time attribute

        # Syncing the slash commands (if needed)
        await bot.tree.sync()
        print(datetime.datetime.now())
