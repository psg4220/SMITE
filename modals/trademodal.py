import discord
from decimal import Decimal
from discord import app_commands
from discord.ext import commands
from utilities.tools import separate_account_number,  validate_decimal
from services.currencyservice import CurrencyService
from services.tradeservice import TradeService, TradeType
from models.currency import Currency
from models.trade import TradeList

class TradeModal(discord.ui.Modal, title="Create a trade"):
    price = discord.ui.TextInput(
        label="Price",
        placeholder="Price per unit",
        max_length=18
    )
    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="Amount of units to be traded",
        max_length=18
    )

    def __init__(self, bot: commands.Bot, trade_type: TradeType,
                 base_currency: Currency, quote_currency: Currency, view: discord.ui.View):
        super().__init__()
        self.bot = bot
        self.trade_type = trade_type
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        price = self.price.value
        amount = self.amount.value

        base_ticker = self.base_currency.ticker
        quote_ticker = self.quote_currency.ticker

        await interaction.response.defer(ephemeral=True)

        if not validate_decimal(Decimal(price)) and not validate_decimal(Decimal(amount)):
            embed = discord.Embed(
                title="Invalid amount format",
                description="Make sure the amount is not more than 999,999,999,999,999.99\n"
                            "or less than 0.01 or contains any letters, symbols",
                color=0xff0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        result = await TradeService.process_trade(
            discord_id=interaction.user.id,
            trade_type=self.trade_type,
            base_currency_id=self.base_currency.currency_id,
            quote_currency_id=self.quote_currency.currency_id,
            price=Decimal(price),
            amount=Decimal(amount)
        )

        # embed_prompt = ""
        # if self.trade_type == TradeType.BUY:
        #     embed_prompt = (f"You purchased **{Decimal(price) * Decimal(amount)} {quote_ticker.upper()}**\n"
        #                     f"And received **{Decimal(amount)} {base_ticker.upper()}**")
        # else:
        #     embed_prompt = (f"You sold **{Decimal(amount)} {base_ticker.upper()}**\n"
        #                     f"And received **{Decimal(price) * Decimal(amount)} {quote_ticker.upper()}**")
        embed = discord.Embed()

        if self.trade_type == TradeType.BUY:
            total = f"{(Decimal(price) * Decimal(amount)):,.2f} {quote_ticker.upper()}"
        else:
            total = f"{(Decimal(amount)):,.2f} {base_ticker.upper()}"

        if result == 1:
            embed = discord.Embed(
                title="TRADE SUCCESS",
                description=f"Your trade has been fulfilled\n"
                            f"Total: {total}",
                color=0x00ff00,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        elif result == 2:
            embed = discord.Embed(
                title="TRADE SUCCESS",
                description="Trade partially fulfilled and listed\n"
                            f"Total: {total}",
                color=0x00ff00,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        elif result == 3:
            embed = discord.Embed(
                title="INSUFFICIENT FUNDS",
                description="You do not have enough funds\n"
                            f"Total {total}",
                color=0x00ff00,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if self.view:  # If a view is associated, disable buttons
            message = await interaction.original_response()
            await message.edit(embed=embed, view=self.view)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
