import datetime
import os

import discord
from discord import app_commands
from discord.ext import commands
import json
import logging

import Account
import Currency
import InputFormatter
import Trading
import ViewTrade
from Trading import Trade
from Boat import Economy
import WireTransfer

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

if os.path.exists('properties.json'):
    with open("properties.json", "r") as f:
        properties = json.load(f)
else:
    with open("properties.json", "w") as f:
        template = {
            "TOKEN": "",
            "SQLITE_PATH": ""
        }
        f.write(json.dumps(template, indent=4))
    print("No properties.json. Created one.")
    exit(0)


def is_dm(inter: discord.Interaction):
    if inter.guild is None:
        return True
    return False


@bot.event
async def on_ready():
    await Currency.create_tables()
    print(f'We have logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
    except Exception as e:
        print(e)


@bot.tree.command(name="create_currency", description="Creates a new currency. (ONE TIME ONLY)")
@app_commands.describe(
    name="The name of your currency",
    ticker="A ticker symbol (3 or 4 characters long) ",
    initial_supply="The amount of money you want to print"
)
async def create_currency(inter: discord.Interaction, name: str, ticker: str, initial_supply: float):
    try:
        await inter.response.defer(ephemeral=True)
        if is_dm(inter):
            await inter.followup.send(
                "** Use this command in your server. **"
            )
            return
        if inter.guild.owner_id != inter.user.id:
            await inter.followup.send(
                "** You must be an admin to create a currency at this guild. **"
            )
            return
        if not InputFormatter.is_valid_ticker(ticker):
            await inter.followup.send(
                f'> ## ⛔ Failed to create a currency\n'
                f'> ⚠️ Your ticker is not a valid format.\n'
                f'> `Make sure that your ticker doesnt contain symbols, numbers.` \n'
                f'> `Tickers should be 3 or 4 letters long`'
            )
            return
        if not InputFormatter.validate_decimal_places(initial_supply):
            await inter.followup.send(
                f'> ## ⛔ Failed to create a currency\n'
                f'> ⚠️ Maximum of 4 decimal places only.'
            )
            return
        if initial_supply < 0.0001 or initial_supply > 999_999_999_999_999:
            await inter.followup.send(
                f'> ## ⛔ Failed to create a currency\n'
                f'> ⚠️ Initial supply should be less than 999,999,999,999,999 or greater than 0.0001.'
            )
            return
        result = await Currency.create_currency(
            inter.user.id,
            inter.guild_id,
            name,
            ticker,
            initial_supply
        )
        await Currency.set_currency_guild_id(inter.user.id, inter.guild_id)
        if result == 0:
            await inter.followup.send(f'> ## ✅ Currency {name} ({ticker.upper()}) has been created!')
        elif result == -1:
            await inter.followup.send(
                "> ## ⛔ Failed to create a currency ⛔\n"
                "> ⚠️ Make sure that you didn't created any previous currency\n"
                "> ⚠️ And make sure that the currency name does not already exist"
            )
        elif result == -2:
            await inter.followup.send(
                f"> ## ⛔ Failed to create a currency\n"
                "> ⚠️ Server already has a currency"
            )

    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="set_guild", description="Sets the guild id to your currency")
async def set_guild_command(inter: discord.Interaction):
    try:
        await inter.response.defer(ephemeral=True)
        if is_dm(inter):
            await inter.followup.send(
                "> ### You cannot use this bot in a DM. \n"
                "> Please run this command on the server you want to set it."
            )
            return
        result = await Currency.set_currency_guild_id(inter.user.id, inter.guild_id)
        if result == 0:
            await inter.followup.send(
                '> ### Your currency guild has been set'
            )
        elif result == -1:
            await inter.followup.send(
                "> ### Your currency is already set to a guild\n"
                "> ### Or this guild has been already set by someone"
            )
        elif result == -2:
            await inter.followup.send(
                "> ### You haven't created your currency yet."
            )
    except Exception as e:
        await inter.followup.send(e)


@bot.tree.command(name="unset_guild",
                  description="unsets the guild id to your currency "
                              "(WARNING: if left unset anyone could /set_guild your server)")
async def unset_guild_command(inter: discord.Interaction):
    try:
        await inter.response.defer(ephemeral=True)
        if is_dm(inter):
            await inter.followup.send(
                "> ### You cannot use this bot in a DM. \n"
                "> Please run this command on the server you want to set it."
            )
            return
        result = await Currency.unset_currency_guild_id(inter.user.id)
        if result == 0:
            await inter.followup.send(
                '> ### Your currency guild has been unset'
            )
        elif result == -1:
            await inter.followup.send(
                "> ### You haven't created your currency yet."
            )
        elif result == -2:
            await inter.followup.send(
                "> ### You do not own this server."
            )
    except Exception as e:
        await inter.followup.send(e)


@bot.tree.command(name="set_auth_provider", description="Sets the guild authentication token for the provider")
@app_commands.choices(
    provider=[
        app_commands.Choice(name="UnbelievaBoat", value=WireTransfer.Provider.UNBELIEVABOAT.value),
    ]
)
async def set_auth_command(inter: discord.Interaction, provider: app_commands.Choice[int], auth: str):
    try:
        await inter.response.defer(ephemeral=True)
        if not await Currency.is_authorized_user(inter.user.id, inter.guild_id):
            await inter.followup.send(
                '> ### You do not have permission to use this command'
            )
            return
        match provider.value:
            case WireTransfer.Provider.UNBELIEVABOAT.value:
                result = await Currency.create_provider_auth(inter.user.id,
                                                             inter.guild_id,
                                                             WireTransfer.Provider(provider.value),
                                                             auth)

                if result == -1:
                    await Currency.set_provider_auth(inter.user.id,
                                                     inter.guild_id,
                                                     WireTransfer.Provider(provider.value),
                                                     auth)
                elif result == -2:
                    await inter.followup.send(
                        '> ### You havent created a currency yet'
                    )
                    return
                await inter.followup.send("> ### Auth provider has been set")
            case _:
                return
    except Exception as e:
        await inter.followup.send(e)


@bot.tree.command(name="address",
                  description="Shows your receiver address")
@app_commands.describe(_input='What currency you want to input (add $ if it is a ticker ex. $USD')
async def address_command(inter: discord.Interaction, _input: str):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        if _input.startswith("$"):
            ticker = _input[1:]
            result = await Currency.get_account_id(inter.user.id, ticker, Currency.InputType.TICKER.value)
        else:
            ticker = await Currency.get_currency_ticker(_input, Currency.InputType.CURRENCY_NAME.value)
            result = await Currency.get_account_id(inter.user.id, _input, Currency.InputType.CURRENCY_NAME.value)
        if result is None:
            await inter.followup.send(
                f"> ## ⛔ Currency doesn't exist ⛔\n"
            )
            return
        await inter.followup.send(
            f"> ## Your {ticker.upper()} address is:\n"
            f"> || **{result}** ||"
        )
    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="balance", description="Displays the balance of your specified currency.")
@app_commands.describe(_input="What currency you want to input (add $ if it is a ticker ex. $USD)")
async def balance_command(inter: discord.Interaction, _input: str):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        if _input.startswith('$'):
            ticker = _input[1:]
            balance = await Currency.view_balance(inter.user.id, ticker, Currency.InputType.TICKER.value)
        else:
            balance = await Currency.view_balance(inter.user.id, _input, Currency.InputType.CURRENCY_NAME.value)
            ticker = await Currency.get_currency_ticker(_input, Currency.InputType.CURRENCY_NAME.value)
        if balance is None:
            await inter.followup.send(
                "> ## ⛔ Name doesn't exist ⛔\n"
            )
            return
        await inter.followup.send(
            f"> ## Your {ticker.upper()} Balance:\n"
            f"> # {balance:,.4f}"
        )
    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="transfer", description="Transfers funds to the specified address")
@app_commands.describe(
    receiver_address="Address that you are going to send to.",
    amount="The amount of funds that you want to send."
)
async def transfer(inter: discord.Interaction, receiver_address: str, amount: float):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        if not InputFormatter.validate_decimal_places(amount):
            await inter.followup.send(
                "> ## ⚠️ Maximum number of decimal places is reached (4 max)"
            )
            return

        if amount < 0.0001 or amount > 999_999_999_999_999:
            await inter.followup.send("> ## ⚠️ Amount should not be below 0.0001 and above 999,999,999,999,999")
            return

        currency_name = await Currency.get_currency_name(receiver_address, Currency.InputType.ACCOUNT_ID.value)
        currency_ticker = await Currency.get_currency_ticker(receiver_address, Currency.InputType.ACCOUNT_ID.value)
        if currency_name is None or currency_ticker is None:
            await inter.followup.send(
                "> ## ⛔ TRANSFER FAILED ⛔\n"
                "> ⚠️ **Your address in this currency doesn't exist**",
            )
            return
        await inter.followup.send(
            f"> ## ⚠️You are about to transfer ***{amount:,.4f}*** amount of ***{currency_name}({currency_ticker})***\n"
            f"> ## to this given receiver address\n"
            f"> ## ({receiver_address})\n"
            "> ### Click confirm to transfer",
            view=ConfirmTransfer(inter.user.id, receiver_address, amount)
        )
    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


class ConfirmTransfer(discord.ui.View):
    def __init__(self, discord_id: int, receiver_address: str, amount: float):
        super().__init__()
        self.discord_id = discord_id
        self.receiver_address = receiver_address
        self.amount = amount

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm_command(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        result = await Currency.transfer(self.discord_id, self.receiver_address, self.amount)
        if isinstance(result, tuple):
            await interaction.followup.send(
                f"> ## ✅ TRANSFER COMPLETED\n\n"
                "> Transaction Receipt UUID:\n"
                f"> **{result[0]}**\n"
            )
            discord_id_receiver = await bot.fetch_user(result[1])
            await discord_id_receiver.send(
                f"> ## 💸You Received {self.amount:,.4f} of {result[2]}({result[3]})\n"
                f"> ### 🧾Transaction Receipt UUID:\n"
                f"> `{result[0]}`"
            )
        elif result == -1:
            await interaction.followup.send(
                "> ## ⛔ TRANSFER FAILED ⛔\n"
                f"> ⚠️ **Amount ({self.amount}) cannot be less than or equal to zero**"
            )
        elif result == -2:
            await interaction.followup.send(
                "> ## ⛔ TRANSFER FAILED ⛔\n"
                "> ⚠️ **Receiver address doesn't exist**"
            )
        elif result == -3:
            await interaction.followup.send(
                "> ## ⛔ TRANSFER FAILED ⛔\n"
                "> ⚠️ **Your address in this currency doesn't exist**",
            )
        elif result == -4:
            await interaction.followup.send(
                "> ## ⛔ TRANSFER FAILED ⛔\n"
                "> ⚠️ **Insufficient Funds**",
            )
        elif result == -5:
            await interaction.followup.send(
                "> ## ⛔ TRANSFER FAILED ⛔\n"
                "> ⚠️ **You cannot send funds to your own address**",
            )
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send('Cancelled')
        self.stop()


@bot.tree.command(name="address_info", description="Checks the info of the address.")
@app_commands.describe(
    address="The address"
)
async def address_info_command(inter: discord.Interaction, address: str):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        is_central = await Currency.is_central(address)
        currency_name = await Currency.get_currency_name(address, Currency.InputType.ACCOUNT_ID.value)
        currency_ticker = await Currency.get_currency_ticker(address, Currency.InputType.ACCOUNT_ID.value)
        if currency_name is None or currency_ticker is None:
            await inter.followup.send(
                f"> ### Currency does not exist."
            )
        if is_central:
            await inter.followup.send(
                f"> ### 🏦 This is the MAIN address of the currency\n"
                f"> ### {currency_name} ({currency_ticker})"
            )
            return
        await inter.followup.send(
            f"> ### {currency_name} ({currency_ticker})"
        )
    except Exception as e:
        await inter.followup.send("Something went wrong:\n", e)
        raise e


@bot.tree.command(name="info", description="Views the info of a currency.")
@app_commands.describe(
    _input="What currency you want to input (add $ if it is a ticker ex. $USD)"
)
async def info_command(inter: discord.Interaction, _input: str):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        if _input.startswith("$"):
            ticker = _input[1:]
            currency_id = await Currency.get_currency_id(ticker, Currency.InputType.TICKER.value)
            name = await Currency.get_currency_name(ticker, Currency.InputType.TICKER.value)
        else:
            currency_id = await Currency.get_currency_id(_input, Currency.InputType.CURRENCY_NAME.value)
            ticker = await Currency.get_currency_ticker(_input, Currency.InputType.CURRENCY_NAME.value)
            name = _input

        if currency_id is None:
            await inter.followup.send(
                f"> ### Currency does not exist."
            )
            return

        max_supply = await Currency.get_maximum_supply(currency_id)
        reserve_supply = await Currency.get_reserve_supply(currency_id)

        if max_supply is None or reserve_supply is None:
            await inter.followup.send(
                f"> `Max and reserve supply doesn't exist (which is impossible).`\n"
                f"> `Report this in the SMITE discord server.`"
            )
            return
        trade_supply = await Currency.get_active_trades_supply(currency_id)
        circulation_supply = (max_supply - reserve_supply)
        date_creation_unix = await Currency.get_central_date_creation(currency_id)
        date_creation = datetime.datetime.fromtimestamp(date_creation_unix, tz=datetime.UTC) \
            .strftime("%b%e, %Y%l:%M:%S %p")
        await inter.followup.send(
            f"`Currency Information`\n\n"
            f"`Currency Name: {name}`\n"
            f"`Ticker Symbol: {ticker.upper()}`\n"
            f"`Maximum Supply: {max_supply:,.4f}`\n"
            f"`Reserve Supply: {reserve_supply:,.4f}`\n"
            f"`In Circulation: {circulation_supply:,.4f}`\n"
            f"`In Trading: {trade_supply:,.4f}`\n"
            f"`Date Created: {date_creation}`"
        )

    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="receipt", description="Checks the transaction uuid.")
@app_commands.describe(
    transaction_uuid="The transaction uuid."
)
async def receipt_command(inter: discord.Interaction, transaction_uuid: str):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        result = await Currency.get_transaction_info(transaction_uuid)
        if result is None:
            await inter.followup.send(
                "> ⛔ Transaction not found ⛔"
            )
            return
        await inter.followup.send(
            "> ### Transaction Receipt\n"
            f"> `Currency name: {result[1]}`\n"
            f"> `Sender Address: {Account.from_bytes(result[2])}`\n"
            f"> `Receiver Address: {Account.from_bytes(result[3])}`\n"
            f"> `Amount: {result[4]:,.4f}`\n"
            f"> `Transaction Date: {datetime.datetime.fromtimestamp(result[5], tz=datetime.UTC)}`"
        )
    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="trade", description="Trades currencies to the market.")
@app_commands.describe(
    trade_type='Type either "buy" or "sell"',
    base_ticker="The base currency's ticker name",
    quote_ticker="The quote currency's ticker name",
    price="The price that you are willing to pay for one currency",
    amount="How many do you want to buy"
)
@app_commands.choices(
    trade_type=[
        app_commands.Choice(name="BUY", value="b"),
        app_commands.Choice(name="SELL", value="s")
    ]
)
async def trade_command(inter: discord.Interaction,
                        trade_type: app_commands.Choice[str],
                        base_ticker: str,
                        quote_ticker: str,
                        price: str,
                        amount: str):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        match trade_type.value:
            case 'buy' | 'b':
                trade_type = Trading.TradeType.BUY
            case 'sell' | 's':
                trade_type = Trading.TradeType.SELL
            case _:
                await inter.followup.send(
                    f"> ### Invalid trade type"
                )
                return
        trade = Trade(
            trade_type=trade_type,
            base_ticker=base_ticker,
            quote_ticker=quote_ticker,
            price=float(price),
            amount=float(amount)
        )
        result = await Currency.trade(inter.user.id, trade)

        if result == -1:
            await inter.followup.send(
                f"> ## ❌Trade failed\n"
                f"> ### Insufficient Funds"
            )
            return
        if result == -2:
            await inter.followup.send(
                f"> ## ⛔ Trade failed\n"
                f"> ### Base or Quote ticker does not exist\n"
            )
            return
        if result[0] == 1:
            await inter.followup.send(
                f"> ## ✅{'Buy' if result[2] else 'Sell'} Order listed\n"
                f"> ⚠️ Copy this: `Trade Number: {result[1]}`\n"
                f"> `Note: If list takes too long to fulfill, consider adjusting the price and or amount.`"
            )
        elif result[0] == 0:
            await inter.followup.send(
                f"> ### ✅Bought currency"
            )
            if result[3]:
                receiver = await bot.fetch_user(result[1])
                await receiver.send(
                    f"> ## 💱✅Your Trade (№ {result[2]}) has been fulfilled."
                )
    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="trade_cancel", description="Closes a trade")
@app_commands.describe(trade_number="The trade number when you list a trade")
async def close_trade(inter: discord.Interaction, trade_number: int):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        result = await Currency.cancel_trade(inter.user.id, trade_number)
        if result == 0:
            await inter.followup.send(
                f"> ## 📪 Trade Order Closed"
            )
        elif result == -1:
            await inter.followup.send(
                f"> ## ⛔ Fail to Close trade\n"
                f"> ### ⚠️ Trade doesn't exist!\n"
            )
        elif result == -2:
            await inter.followup.send(
                f"> ## ⛔ Fail to Close trade\n"
                f"> ### ⚠️ Trade is not yours!\n"
            )
    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="chart", description="Views the Chart of a market")
@app_commands.choices(
    scale=[
        app_commands.Choice(name="1 SECOND", value="1s"),
        app_commands.Choice(name="1 MINUTE", value="1m"),
        app_commands.Choice(name="1 HOUR", value="1h"),
        app_commands.Choice(name="1 DAY", value="1d"),
        app_commands.Choice(name="2 DAYS", value="2d"),
        app_commands.Choice(name="1 WEEK", value="1w"),
        app_commands.Choice(name="1 MONTH", value="1mnt")
    ]
)
async def chart_command(inter: discord.Interaction,
                        base_ticker: str,
                        quote_ticker: str,
                        scale: app_commands.Choice[str] = "1s",
                        limit: int = 500):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        match scale.value if isinstance(scale, str) else scale:
            case '1s':
                chosen_scale = ViewTrade.TimeScale.SECOND
            case '1m' | '60s':
                chosen_scale = ViewTrade.TimeScale.MINUTE
            case '1h' | '60m':
                chosen_scale = ViewTrade.TimeScale.HOUR
            case '1d' | '24h':
                chosen_scale = ViewTrade.TimeScale.DAY
            case '2d' | '48h':
                chosen_scale = ViewTrade.TimeScale.DAY_2
            case '1w' | '7d':
                chosen_scale = ViewTrade.TimeScale.WEEK
            case '1mnt':
                chosen_scale = ViewTrade.TimeScale.MONTH
            case _:
                await inter.followup.send(
                    "> ### ⛔ Invalid scale input"
                )
                return

        buffer = await ViewTrade.plot_trade_logs(
            properties['SQLITE_PATH'],
            base_ticker.upper(),
            quote_ticker.upper(),
            chosen_scale,
            None if limit <= 0 else limit
        )
        if buffer is None:
            await inter.followup.send(
                "> ### No charts available"
            )
            return
        chart_image = discord.File(buffer, filename="chart.png")
        buffer.close()
        bid_ask = await Currency.get_bid_ask_price(base_ticker, quote_ticker)
        spread = 0
        if bid_ask[0] is not None and bid_ask[1] is not None:
            spread = abs(bid_ask[0] - bid_ask[1])
        await inter.followup.send(f"> # {base_ticker.upper()}/{quote_ticker.upper()}\n"
                                  f"> # {await Currency.last_trade_price(base_ticker, quote_ticker):,.4f} {quote_ticker.upper()}\n"
                                  f"> ## 🟩 Bid: {bid_ask[0]} | 🟥 Ask: {bid_ask[1]}\n"
                                  f"> ## Spread: {abs(spread)}",
                                  file=chart_image)

    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="mint", description="Creates new money (Prints more money)")
@app_commands.describe(amount="Amount that you want to mint")
async def mint_command(inter: discord.Interaction, amount: float):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        if not InputFormatter.validate_decimal_places(amount):
            await inter.followup.send(
                f"> ## ⛔ Fail to mint\n"
                f"> ### Maximum number of decimal places reached (4 max)"
            )
        result = await Currency.mint_currency(inter.user.id, amount)
        if result == 0:
            await inter.followup.send(
                f"> ## 🖨️ Minted {amount} successfully"
            )
        elif result == -1:
            await inter.followup.send(
                f"> ## ⛔ Fail to mint\n"
                f"> ### Amount should not be less than 0.0001"
            )
        elif result == -2:
            await inter.followup.send(
                f"> ## ⛔ Fail to mint\n"
                f"> ### Currency has not been created yet"
            )
        # elif result == -3:
        #     await inter.followup.send(
        #         f"> ## ⛔ Fail to mint\n"
        #         f"> ### Balance is less than 0.0001"
        #     )
        elif result == -4:
            await inter.followup.send(
                f"> ## ⛔ Fail to mint\n"
                f"> ### Balance is greater than 999,999,999,999,999"
            )

    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="burn", description="Burns money (Destroys money)")
@app_commands.describe(amount="Amount that you want to burn")
async def burn_command(inter: discord.Interaction, amount: float):
    try:
        await inter.response.defer(ephemeral=True)
        # if not is_dm(inter):
        #     await inter.followup.send(
        #         "** You cannot use this bot in a server, DM me instead. **"
        #     )
        #     return
        if not InputFormatter.validate_decimal_places(amount):
            await inter.followup.send(
                f"> ## ⛔ Fail to burn\n"
                f"> ### Maximum number of decimal places reached (4 max)"
            )
        result = await Currency.mint_currency(inter.user.id, amount, is_subtract=True)
        if result == 0:
            await inter.followup.send(
                f"> ## 🔥 Burned {amount} successfully"
            )
        elif result == -1:
            await inter.followup.send(
                f"> ## ⛔ Fail to burn\n"
                f"> ### Amount should not be less than 0.0001"
            )
        elif result == -2:
            await inter.followup.send(
                f"> ## ⛔ Fail to burn\n"
                f"> ### Currency has not been created yet"
            )
        elif result == -3:
            await inter.followup.send(
                f"> ## ⛔ Fail to burn\n"
                f"> ### Exceeded the balance"
            )
        # elif result == -4:
        #     await inter.followup.send(
        #         f"> ## ⛔ Fail to burn\n"
        #         f"> ### Balance is greater than 999,999,999,999,999"
        #     )

    except Exception as e:
        await inter.followup.send(f"Something went wrong:\n{e}")
        raise e


@bot.tree.command(name="wire_transfer", description="Transfer funds to using other bots.")
@app_commands.choices(
    provider=[
        app_commands.Choice(name="UnbelievaBoat", value=WireTransfer.Provider.UNBELIEVABOAT.value),
    ]
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="DEPOSIT", value=1),
        app_commands.Choice(name="WITHDRAW", value=0),
    ]
)
async def wire_transfer_command(inter: discord.Interaction,
                                provider: app_commands.Choice[int],
                                action: app_commands.Choice[int],
                                amount: int):
    try:
        await inter.response.defer(ephemeral=True)
        if is_dm(inter):
            await inter.followup.send(
                "> ### You cannot use this bot in a DM."
            )
            return
        match provider.value:
            case WireTransfer.Provider.UNBELIEVABOAT.value:
                result = await boat_transfer(inter.user.id, inter.guild_id, action.value, amount)
                if result == 0:
                    await inter.followup.send(
                        "> ### Wire transfer successful"
                    )
                elif result == -1:
                    await inter.followup.send(
                        "> ### Insufficient Funds"
                    )
                elif result == -2:
                    await inter.followup.send(
                        "> ### Provider's currency does not exist"
                    )
                elif result == -3:
                    await inter.followup.send(
                        "> ### Wire Transfer Failed.\n"
                        "> ### Please contact server admin immediately."
                    )
            case _:
                await inter.followup.send(
                    "> ### Provider not supported"
                )
    except Exception as e:
        await inter.followup.send(e)


async def boat_transfer(discord_id: int, guild_id: int, action, amount):
    try:
        auth = await Currency.get_provider_auth(guild_id, WireTransfer.Provider.UNBELIEVABOAT)
        if auth is None:
            return -3
        economy = Economy(discord_id, guild_id, auth)
        boat = WireTransfer.BoatTransfer(economy)
        return await boat.transfer(amount, WireTransfer.Action(action))
    except Exception as e:
        raise e

@bot.tree.command(name="currencies", description="List of all currencies")
@app_commands.choices(
    order=[
        app_commands.Choice(name="FIRST", value=0),
        app_commands.Choice(name="RECENT", value=1),
    ]
)
@app_commands.describe(order="Shows the list from FIRST or RECENT", page="The page")
async def currencies_command(inter: discord.Interaction, order: app_commands.Choice[int], page: int = 1):
    try:
        await inter.response.defer()
        currencies = await Currency.get_currencies(page=page, show_last=True if order.value == 1 else False)
        currencies_display = "> `Currencies List`\n"
        for c in currencies:
            currencies_display += f"> `{c[0]} | {c[1]}`\n"
        await inter.followup.send(currencies_display)
    except Exception as e:
        await inter.followup.send(e)


@bot.tree.command(name="edit_currency", description="Debug")
async def edit_currency_command(inter: discord.Interaction, new_name: str, new_ticker: str):
    try:
        await inter.response.defer(ephemeral=True)
        if is_dm(inter):
            await inter.followup.send(
                "> ### Execute this command in your server."
            )
            return
        if inter.guild.owner_id != inter.user.id:
            await inter.followup.send(
                "> ### You do not have the permission to use this command."
            )
            return
        await Currency.update_currency(inter.guild_id, new_name, new_ticker)
        await inter.followup.send(
            "> ## Your currency has been edited."
        )
    except Exception as e:
        await inter.followup.send(e)


# @bot.tree.command(name="test", description="Debug")
# async def test(inter: discord.Interaction):
#     try:
#         await inter.response.defer()
#         id = await Currency.get_currency_id(inter.guild_id, Currency.InputType.GUILD_ID.value)
#         if id is None:
#             id = "None"
#         await inter.followup.send(id)
#     except Exception as e:
#         await inter.followup.send(e)


# class Questionnaire(discord.ui.Modal, title='Questionnaire Response'):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#
#         self.add_item(discord.ui.TextInput(label="Amount"))
#     async def buy(self, interaction: discord.Interaction, button: discord.Button):
#         pass
#     async def on_submit(self, interaction: discord.Interaction) -> None:
#         embed = discord.Embed(title="test")
#         embed.add_field(name="Value", value=self.children[0])
#         await interaction.response.send_message(embeds=[embed])

bot.run(properties['TOKEN'], log_handler=handler)
