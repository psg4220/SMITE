import discord
from decimal import Decimal
from discord import app_commands
from discord.ext import commands
from utilities.tools import separate_account_number,  validate_decimal
from services.accountservice import AccountService
from services.currencyservice import CurrencyService
from services.roleservice import RoleService
from services.boatwiretransferservice import BoatAuthListService
from wrapper.unbelievaboat.boatclient import BoatClient


class BoatWireTransferModal(discord.ui.Modal, title="UnbelievaBoat Wire Transfer"):
    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="Amount to be transferred",
        max_length=18
    )

    def __init__(self,bot: commands.Bot, transfer_type: str):
        super().__init__()
        self.bot = bot
        self.transfer_type = transfer_type

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        amount = self.amount.value
        token = await BoatAuthListService.get_token_by_guild_id(interaction.guild_id)

        if not amount.isdigit():
            embed = discord.Embed(
                title="Invalid Format",
                description=f"Amount must contain a whole number",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
            return

        if not token:
            embed = discord.Embed(
                title="An error occured",
                description=f"The UnbelievaBoat of this server doesn't support SMITE\n"
                            "Please contact the owner for more details",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
            return

        if self.transfer_type == "transfer_in":
            balance = await BoatClient.get_balance(guild_id=interaction.guild_id,
                                             discord_id=interaction.user.id,
                                             auth_token=token.token)
            if balance['bank'] < int(amount):
                embed = discord.Embed(
                    title="TRANSFER FAILED",
                    description=f"Insufficient Funds",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            updated_boat_account = await BoatClient.update_balance(-int(amount),
                                            guild_id=interaction.guild_id,
                                            discord_id=interaction.user.id,
                                            auth_token=token.token)
            if len(updated_boat_account) == 1:
                embed = discord.Embed(
                    title="TRANSFER FAILED",
                    description=f"This is likely an authorization error\n"
                                f"If this error persist please contact the server admin",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            account = await AccountService.get_account(interaction.user.id, token.currency_id)
            account.balance += int(amount)
            updated_account = await AccountService.update_account_balance(account.account_id, account.balance)

            embed = discord.Embed(
                title="FUNDS TRANSFERRED",
                description=f"You have transferred {amount} in to SMITE",
                color=0x00ff00
            )

            await interaction.followup.send(embed=embed)
        else:
            account = await AccountService.get_account(interaction.user.id, token.currency_id)

            if account.balance < int(amount):
                embed = discord.Embed(
                    title="TRANSFER FAILED",
                    description=f"Insufficient Funds",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            updated_boat_account = await BoatClient.update_balance(int(amount),
                                            guild_id=interaction.guild_id,
                                            discord_id=interaction.user.id,
                                            auth_token=token.token)
            if len(updated_boat_account) == 1:
                embed = discord.Embed(
                    title="TRANSFER FAILED",
                    description=f"This is likely an authorization error\n"
                                f"If this error persist please contact the server admin",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            account.balance -= int(amount)
            updated_account = await AccountService.update_account_balance(account.account_id, account.balance)
            embed = discord.Embed(
                title="FUNDS TRANSFERRED",
                description=f"You have transferred {amount} to UnbelievaBoat",
                color=0x00ff00
            )

            await interaction.followup.send(embed=embed)

