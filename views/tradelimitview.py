import io
import discord
from datetime import timedelta
from discord import Interaction
from discord.ext import commands
from discord.ui import View, Button, Select
from modals.trademodal import TradeModal
from models.tradelog import TradeLog
from models.currency import Currency
from services.tradeservice import TradeType, TradeService
from services.tradelogservice import TradeLogService
from plotting.chartplotter import ChartPlotter

class TradeLimitView(View):
    def __init__(self, bot: commands.Bot, base_currency: Currency,
                 quote_currency: Currency, embed: discord.Embed,
                 user: discord.User, chart: ChartPlotter = None,
                 timeout: float = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.embed = embed
        self.user = user
        self.chart = chart
        self.base_currency = base_currency
        self.quote_currency = quote_currency

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

    @discord.ui.button(label="BUY", style=discord.ButtonStyle.green, custom_id="buy_button", emoji="🐂")
    async def buy_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(
            TradeModal(self.bot, TradeType.BUY,
                       base_currency=self.base_currency, quote_currency=self.quote_currency, view=self)
        )

    @discord.ui.button(label="SELL", style=discord.ButtonStyle.red, custom_id="sell_button", emoji="🐻")
    async def sell_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(
            TradeModal(self.bot, TradeType.SELL,
                       base_currency=self.base_currency, quote_currency=self.quote_currency, view=self)
        )

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, custom_id="refresh_button", emoji="🔁")
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        last_trade_log = await TradeLogService.get_last_trade_log(self.base_currency.currency_id, self.quote_currency.currency_id)
        embed = await display_trade_info(last_trade_log, self.base_currency, self.quote_currency)
        self.embed = embed[0]
        self.chart = embed[1]
        await interaction.message.edit(embed=embed[0], view=self, attachments=[embed[2]])

    @discord.ui.select(
        placeholder="⏳ Time Frame",
        options=[
            discord.SelectOption(label="1min", description="1 MINUTE", value="60"),
            discord.SelectOption(label="5min", description="5 MINUTES", value="300"),
            discord.SelectOption(label="10min", description="10 MINUTES", value="600"),
            discord.SelectOption(label="30min", description="30 MINUTES", value="1800"),
            discord.SelectOption(label="1h", description="1 HOUR", value="3600"),
            discord.SelectOption(label="2h", description="2 HOURS", value="7200"),
            discord.SelectOption(label="4h", description="4 HOURS", value="14400"),
            discord.SelectOption(label="8h", description="8 HOURS", value="28800"),
            discord.SelectOption(label="12h", description="12 HOURS", value="43200"),
            discord.SelectOption(label="1d", description="1 DAY", value="86400"),
            discord.SelectOption(label="2d", description="2 DAYS", value="172800"),
            discord.SelectOption(label="7d", description="7 DAYS", value="604800"),
            discord.SelectOption(label="30d", description="1 MONTH", value="2592000"),
            discord.SelectOption(label="1y", description="1 YEAR", value="31558000")

        ]
    )
    async def select_timeframe(self, interaction: discord.Interaction, select: Select):
        """
        Handles the interaction when an option is selected.
        """
        await interaction.response.defer()
        timeframe = select.values[0]
        self.chart.time_period = timedelta(seconds=int(timeframe))
        image = await self.chart.generate_chart()
        discord_image = discord.File(io.BytesIO(image), filename="chart.png")
        self.embed.set_image(url="attachment://chart.png")
        await interaction.message.edit(embed=self.embed, view=self, attachments=[discord_image])

    @discord.ui.select(
        placeholder="📈 Chart Type",
        options=[
            discord.SelectOption(label="LINE", description="Line Chart", value="line"),
            discord.SelectOption(label="CANDLESTICK", description="Japanese candlestick chart", value="candlestick")
        ]
    )
    async def select_chart_type(self, interaction: discord.Interaction, select: Select):
        await interaction.response.defer()
        chart_type = select.values[0]
        self.chart.chart_type = chart_type
        image = await self.chart.generate_chart()
        discord_image = discord.File(io.BytesIO(image), filename="chart.png")
        self.embed.set_image(url="attachment://chart.png")
        await interaction.message.edit(embed=self.embed, view=self, attachments=[discord_image])


    async def on_timeout(self):
        """
        Handle the view's timeout by disabling buttons.
        """
        for item in self.children:
            item.disabled = True
        # Optionally, edit the original message to reflect the timeout.
        # Ensure you have access to the original message.
        try:
            message = await self.message  # Reference the original message containing this view.
            await message.edit(content="The trading view timed out!", view=self)
        except AttributeError:
            pass


async def display_trade_info(
        last_trade_log: TradeLog,
        base_currency: Currency,
        quote_currency: Currency
) -> discord.Embed | tuple[discord.Embed, ChartPlotter, discord.File]:

    if not last_trade_log:
        embed = discord.Embed(
            title=f"{base_currency.ticker.upper()}/{quote_currency.ticker.upper()}",
            description=f"### No trade history found\nTry checking the opposite pair",
            color=0x808080
        )
        return embed

    bid_price = await TradeService.get_bid_price(base_currency.currency_id, quote_currency.currency_id)
    ask_price = await TradeService.get_ask_price(base_currency.currency_id, quote_currency.currency_id)

    day_percentage = await TradeLogService.calculate_percentage(base_currency.currency_id,
                                                                quote_currency.currency_id,
                                                                time_delta=timedelta(days=1))

    color = 0x808080
    if day_percentage:
        if day_percentage[len(day_percentage) - 1] > 0:
            color = 0x00ff00
        elif day_percentage[len(day_percentage) - 1] < 0:
            color = 0xff0000

    embed = discord.Embed(color=color)
    embed.title = f"{base_currency.ticker.upper()}/{quote_currency.ticker.upper()}"
    embed.description = f"# {last_trade_log.price:,.2f} {quote_currency.ticker.upper()}"
    embed.add_field(name="🟢 BID", value=f"{bid_price:,.2f}")
    embed.add_field(name="🔴 ASK", value=f"{ask_price:,.2f}")

    chart = ChartPlotter(
        base_currency_id=base_currency.currency_id,
        quote_currency_id=quote_currency.currency_id,
        time_period=timedelta(days=1)
    )

    if day_percentage:
        embed.add_field(name="24hr %", value=f"{day_percentage[len(day_percentage) - 1]:.2f}%", inline=False)

    image = await chart.generate_chart()
    discord_image = discord.File(io.BytesIO(image), filename="chart.png")
    embed.set_image(url="attachment://chart.png")
    return embed, chart, discord_image
