import discord
import asyncio
import logging
from discord.ext import commands
import os
import sys
from dotenv import load_dotenv

# Set up logging to file
logging.basicConfig(
    filename="bot_errors.log",  # Log to a file named "bot_errors.log"
    level=logging.ERROR,  # Log error level and above (ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log message format
)

# # StreamHandler for console output
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.ERROR)
# console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
# logging.getLogger().addHandler(console_handler)


# Define a custom exception hook to log uncaught exceptions
def log_uncaught_exception(exc_type, exc_value, exc_tb):
    if exc_type == KeyboardInterrupt:
        # Ignore keyboard interrupts (e.g. when the bot is shut down)
        pass
    else:
        logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))


# Set the custom exception hook
sys.excepthook = log_uncaught_exception

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix=["!", "?", "&"], intents=intents)


# Event: Bot is ready
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync slash commands globally
    print(f"Bot is online as {bot.user}")
    print("Slash commands synced!")


# Function to dynamically load cogs
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename}")
            except Exception as e:
                print(f"Failed to load cog {filename}: {e}")


# Run the bot
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


asyncio.run(main())
