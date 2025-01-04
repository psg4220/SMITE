import datetime

import discord
import time
from decimal import Decimal
from discord import app_commands
from discord.ext import commands

from models import Transaction
from services.accountservice import AccountService
from services.currencyservice import CurrencyService
from modals.transfermodal import TransferModal
from utilities.tools import validate_decimal

class TransferCog(commands.GroupCog, group_name="transfer"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Guide for Transfer")
    async def help(self, interaction: discord.Interaction) -> None:
        description = """        
        **/transfer funds <ticker> <user> <amount>**
        **/transfer funds**
        
        Transfers your money into a user. You can just enter `/transfer funds`
        and input the **account number** of the receiver.
        
        """

        embed = discord.Embed(
            title="GUIDE TO TRANSFER FUNDS",
            description=description
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="funds", description="Transfers funds to someone")
    async def transfer(self, interaction: discord.Interaction,
                       ticker: str = None, user: discord.User = None,
                       amount: str = None) -> None:

        # If fields are not empty
        if ticker and user and amount:
            # Retrieve the currency
            currency = await CurrencyService.read_currency_by_ticker(ticker.upper())

            # Handle if currency doesnt exist
            if not currency:
                embed = discord.Embed(
                    title="Currency doesn't exist",
                    description="The currency ticker that you have entered doesn't exist\n"
                                "Please check your currency ticker again",
                    color=0xff0000,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check amount contains letters
            if amount.isalpha():
                embed = discord.Embed(
                    title="Amount is not a number",
                    description="Amount shall be a number",
                    color=0xff0000,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            receiver_account = await AccountService.get_account(user.id, currency.currency_id)
            total_balance = receiver_account.balance + Decimal(amount)

            # Check max and min amount
            if not validate_decimal(Decimal(total_balance)):
                embed = discord.Embed(
                    title="Maximum or minimum range exceeded",
                    description="It shall be less than 999,999,999,999,999.99\n"
                                "and more than 0.01",
                    color=0xff0000,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return


            transfer_result = await AccountService.transfer(
                interaction.user.id,
                user.id,
                currency.currency_id,
                Decimal(amount)
            )

            if isinstance(transfer_result, Transaction):
                try:
                    embed = discord.Embed(
                        title="TRANSFER RECEIVED",
                        description=f"You received **{transfer_result.amount} {ticker.upper()}** to **{user.name}**.\n"
                                    f"Transaction Receipt: `{transfer_result.uuid}`",
                        color=0x00ff00
                    )
                    user_receiver = await interaction.client.fetch_user(user.id)
                    await user_receiver.send(embed=embed)
                except Exception:
                    pass
                embed = discord.Embed(
                    title="TRANSFER COMPLETE",
                    description=f"You have transferred **{transfer_result.amount} {currency.name}** to **{user.name}**.\n"
                                f"Transaction Receipt: `{transfer_result.uuid}`",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            if transfer_result == -1:
                embed = discord.Embed(
                    title="TRANSFER FAILED",
                    description=f"Transfer amount is zero or negative",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            elif transfer_result == -2:
                embed = discord.Embed(
                    title="TRANSFER FAILED",
                    description=f"Sender's account does not exist for the specified currency.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            elif transfer_result == -5:
                embed = discord.Embed(
                    title="TRANSFER FAILED",
                    description=f"Receiver's account does not exist for the specified currency.\n"
                                f"Tell the receiver to create an {ticker.upper()} account",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            elif transfer_result == -3:
                embed = discord.Embed(
                    title="TRANSFER FAILED",
                    description=f"Sender and receiver accounts are the same",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            elif transfer_result == -4:
                embed = discord.Embed(
                    title="TRANSFER FAILED",
                    description=f"Insufficient balance in the sender's account",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        # Handle transfer if its by account number
        modal = TransferModal(self.bot)
        await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TransferCog(bot))
    # Sync the slash commands to Discord
    @bot.event
    async def on_ready():
        # Initialize the start_time when the bot is ready
        bot.start_time = time.time()  # This sets the start_time attribute

        # Syncing the slash commands (if needed)
        await bot.tree.sync()
        print(datetime.datetime.now())
