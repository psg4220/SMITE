import discord
import time
from discord import app_commands
from discord.ext import commands
from modals.createaccountmodal import CreateAccountModal
from services.accountservice import AccountService
from services.currencyservice import CurrencyService
from services.roleservice import RoleService, RoleType

class AccountCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    group = app_commands.Group(name="account", description="The account command")

    @group.command(name="create", description="Creates your account for a certain currency")
    async def create_account(self, interaction: discord.Interaction) -> None:
        modal = CreateAccountModal(self.bot)
        await interaction.response.send_modal(modal)

    @group.command(name="info", description="Shows info of one of your accounts")
    async def show_balance(self, interaction: discord.Interaction, ticker: str) -> None:
        currency = await CurrencyService.read_currency_by_ticker(ticker.upper())

        if not currency:
            embed = discord.Embed(
                title="Currency not found",
                description="The currency ticker you provided doesn't exist",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        account = await AccountService.get_account(interaction.user.id, currency.currency_id)

        if not account:
            embed = discord.Embed(
                title="Account doesn't exist",
                description="You have no account on this currency\nPlease create one",
                color=0xff0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        role = await RoleService.get_role(interaction.user.id, currency.currency_id)

        embed = discord.Embed(title="ACCOUNT INFORMATION", color=0xbababa)
        embed.add_field(name="Account Number", value=f"`{ticker.upper()}-{interaction.user.id}`", inline=True)
        embed.add_field(name="Balance", value=f"**{account.balance} {ticker.upper()}**", inline=True)
        embed.add_field(name="Role", value=f"**{'NO ROLE' if not role else RoleType(role.role_number).name}**",
                        inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # @group.command(name="info", description="Views the currency's information")
    # async def currency_information(self, interaction: discord.Interaction) -> None:
    #     pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AccountCog(bot))

    # Sync the slash commands to Discord
    @bot.event
    async def on_ready():
        # Initialize the start_time when the bot is ready
        bot.start_time = time.time()  # This sets the start_time attribute

        # Syncing the slash commands (if needed)
        await bot.tree.sync()
        print("Slash commands synced!")
