import datetime

import discord
from discord.ext import commands
from discord import app_commands
import time


class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_status_info(self):
        """Helper function to get the status data."""
        # Get the bot's latency (ping)
        latency = round(self.bot.latency * 1000)  # Convert to milliseconds

        # Get the bot's uptime
        uptime = time.time() - self.bot.start_time  # Calculate uptime
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)

        # Get the bot's server count
        server_count = len(self.bot.guilds)

        return latency, uptime, hours, minutes, seconds, server_count

    # Prefix command to check bot status
    @commands.command()
    async def status(self, ctx):
        """Shows the bot's status."""
        latency, uptime, hours, minutes, seconds, server_count = self.get_status_info()

        # Send the status message
        embed = discord.Embed(title="Bot Status", color=discord.Color.green())
        embed.add_field(name="Latency", value=f"{latency} ms")
        embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s")
        embed.add_field(name="Servers", value=f"{server_count} servers")
        embed.set_footer(text=f"Requested by {ctx.author.name}")

        await ctx.send(embed=embed)

    # Slash command to check bot status
    @app_commands.command(name="status", description="Displays the bot's status")
    async def slash_status(self, interaction: discord.Interaction):
        """Shows the bot's status (slash command version)."""
        latency, uptime, hours, minutes, seconds, server_count = self.get_status_info()

        # Send the status message
        embed = discord.Embed(title="Bot Status", color=discord.Color.green())
        embed.add_field(name="Latency", value=f"{latency} ms")
        embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s")
        embed.add_field(name="Servers", value=f"{server_count} servers")
        embed.set_footer(text=f"Requested by {interaction.user.name}")

        await interaction.response.send_message(embed=embed)



async def setup(bot):
    await bot.add_cog(StatusCog(bot))  # Await the add_cog() method

    # Sync the slash commands to Discord
    @bot.event
    async def on_ready():
        # Initialize the start_time when the bot is ready
        bot.start_time = time.time()  # This sets the start_time attribute

        # Syncing the slash commands (if needed)
        await bot.tree.sync()
        print(datetime.datetime.now())
