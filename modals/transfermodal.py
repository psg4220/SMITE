import discord
from decimal import Decimal
from discord import app_commands
from discord.ext import commands
from models.transaction import Transaction
from services.currencyservice import CurrencyService
from services.transactionservice import TransactionService
from services.roleservice import RoleService
from services.accountservice import AccountService
from services.currencyservice import CurrencyService
from utilities.tools import separate_account_number,  validate_decimal


class TransferModal(discord.ui.Modal, title="Transfer funds"):
    account_number = discord.ui.TextInput(
        label="Receiver's Account Number",
        placeholder="Enter the receiver's account number",
        max_length=25,
    )
    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="Amount to be sent",
        max_length=25,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        account_number = self.account_number.value
        amount = self.amount.value

        account_ticker, account_discord_id = separate_account_number(account_number)
        currency = await CurrencyService.read_currency_by_ticker(account_ticker.upper())

        # Check amount contains letters
        if amount.isalpha():
            embed = discord.Embed(
                title="Amount is not a number",
                description="Amount shall be a number",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check max and min amount
        if not validate_decimal(Decimal(amount)):
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
            account_discord_id,
            currency.currency_id,
            Decimal(amount)
        )

        if isinstance(transfer_result, Transaction):
            embed = discord.Embed(
                title="TRANSFER RECEIVED",
                description=f"You received **{transfer_result.amount} {account_ticker.upper()}** to **{account_ticker.upper()}-{interaction.user.id}**.\n"
                            f"Transaction Receipt: `{transfer_result.uuid}`",
                color=0x00ff00
            )
            user_receiver = await interaction.client.fetch_user(account_discord_id)
            await user_receiver.send(embed=embed)
            embed = discord.Embed(
                title="TRANSFER COMPLETE",
                description=f"You have transferred **{transfer_result.amount} {account_ticker.upper()}** to **{account_number}**.\n"
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
                description=f"Sender's account does not exist for the specified currency.\n"
                            f"Are you sure you have created already your account?",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        elif transfer_result == -5:
            embed = discord.Embed(
                title="TRANSFER FAILED",
                description=f"Receiver's account does not exist for the specified currency.\n"
                            f"Tell the receiver to create an {amount_ticker.upper()} account",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        elif transfer_result == -6:
            embed = discord.Embed(
                title="TRANSFER FAILED",
                description=f"Sender or receiver account is disabled.",
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
