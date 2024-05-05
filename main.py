import datetime
import os

import discord
from discord import app_commands
from discord.ext import commands
import json
import logging

import Account
import Currency
import NumberFormatter
import Trading
import ViewTrade
from Trading import Trade

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

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
    print("No properties.json. Please input your token and sqlite path on properties.json")
    exit(0)

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
        if not NumberFormatter.validate_decimal_places(initial_supply):
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
            name,
            ticker,
            initial_supply
        )
        if result == 0:
            await inter.followup.send(f'> ## ✅ Currency {name} ({ticker.upper()}) has been created!')
        elif result == -2:
            await inter.followup.send(
                f"> ## ⛔ Failed to create a currency\n"
                "> ⚠️ Special characters are not allowed in ticker"
            )
        elif result == -3:
            await inter.followup.send(
                f"> ## ⛔ Failed to create a currency\n"
                "> ⚠️ Ticker must have a minimum characters of 3 and a maximum of 4"
            )
        else:
            await inter.followup.send(
                "> ## ⛔ Failed to create a currency ⛔\n"
                "> ⚠️ Make sure that you didn't created any previous currency\n"
                "> ⚠️ And make sure that the currency name does not already exist"
            )
    except Exception as e:
        await inter.followup.send("Something went wrong")
        raise e


@bot.tree.command(name="address",
                  description="Shows your receiver address")
@app_commands.describe(_type='Type "name" to search by the currency name or "ticker" to search by ticker ex. (USD)',
                       _input='The search input')
async def address_command(inter: discord.Interaction, _type: str, _input: str):
    try:
        await inter.response.defer(ephemeral=True)

        if _type == 'name' or _type == 'n':
            _type = Currency.InputType.CURRENCY_NAME.value
            result = await Currency.get_account_id(inter.user.id, _input, _type)
        elif _type == 'ticker' or _type == 't':
            _type = Currency.InputType.TICKER.value
            result = await Currency.get_account_id(inter.user.id, _input, _type)
            _input = await Currency.get_currency_name(_input, _type)
        else:
            await inter.followup.send(
                f"> ## ⛔ Invalid type ⛔\n"
                "> **Must be either 'name' or 'ticker' in _type**"
            )
            return
        if result is None:
            await inter.followup.send(
                f"> ## ⛔ Currency doesn't exist ⛔\n"
            )
            return
        await inter.followup.send(
            f"> ## Your {_input} address is:\n"
            f"> || **{result}** ||"
        )
    except Exception as e:
        await inter.followup.send("Something went wrong")
        raise e


@bot.tree.command(name="balance", description="Displays the balance of your specified currency.")
async def balance_command(inter: discord.Interaction, _type: str, _input: str):
    try:
        await inter.response.defer(ephemeral=True)
        if _type == 'name' or _type == 'n':
            _type = Currency.InputType.CURRENCY_NAME.value
            balance = await Currency.view_balance(inter.user.id, _input, _type)
        elif _type == 'ticker' or _type == 't':
            _type = Currency.InputType.TICKER.value
            balance = await Currency.view_balance(inter.user.id, _input, _type)
            _input = await Currency.get_currency_name(_input, _type)
        if balance is None:
            await inter.followup.send(
                "> ## ⛔ Name doesn't exist ⛔\n"
            )
            return
        await inter.followup.send(
            f"> ## Your {_input} Balance:\n"
            f"> # {balance:,.4f}"
        )
    except Exception as e:
        await inter.followup.send("Something went wrong")
        raise e


@bot.tree.command(name="transfer", description="Transfers funds to the specified address")
@app_commands.describe(
    receiver_address="Address that you are going to send to.",
    amount="The amount of funds that you want to send."
)
async def transfer(inter: discord.Interaction, receiver_address: str, amount: float):
    try:
        await inter.response.defer(ephemeral=True)

        if not NumberFormatter.validate_decimal_places(amount):
            await inter.followup.send(
                "> ## ⚠️ Maximum number of decimal places is reached (4 max)"
            )
            return

        if amount < 0.0001 or amount > 999_999_999_999_999:
            await inter.followup.send("> ## ⚠️ Amount should not be below 0.0001 and above 999,999,999,999,999")
            return

        currency_name = await Currency.get_currency_name(receiver_address, Currency.InputType.ACCOUNT_ID.value)
        currency_ticker = await Currency.get_currency_ticker(receiver_address, Currency.InputType.ACCOUNT_ID.value)
        await inter.followup.send(
            f"> ## ⚠️You are about to transfer ***{amount:,.4f}*** amount of ***{currency_name}({currency_ticker})***\n"
            f"> ## to this given receiver address ({receiver_address})\n"
            "> ### Click confirm to transfer",
            view=ConfirmTransfer(inter.user.id, receiver_address, amount)
        )
    except Exception as e:
        await inter.followup.send("Something went wrong")
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
async def info_command(inter: discord.Interaction, address: str):
    try:
        await inter.response.defer(ephemeral=True)
        is_central = await Currency.is_central(address)
        currency_name = await Currency.get_currency_name(address, Currency.InputType.ACCOUNT_ID.value)
        currency_ticker = await Currency.get_currency_ticker(address, Currency.InputType.ACCOUNT_ID.value)
        if is_central:
            await inter.followup.send(
                f"> ### 🏦This is the MAIN address of the currency\n"
                f"> ### {currency_name} ({currency_ticker})"
            )
            return
        await inter.followup.send(
            f"> ### {currency_name} ({currency_ticker})"
        )
    except Exception as e:
        await inter.followup.send("Something went wrong")
        raise e


@bot.tree.command(name="receipt", description="Checks the transaction uuid.")
@app_commands.describe(
    transaction_uuid="The transaction uuid."
)
async def receipt_command(inter: discord.Interaction, transaction_uuid: str):
    try:
        await inter.response.defer(ephemeral=True)
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
        await inter.followup.send("Something went wrong")
        raise e


@bot.tree.command(name="trade", description="Trades currencies to the market.")
@app_commands.describe(
    trade_type='Type either "buy" or "sell"',
    base_ticker="The base currency's ticker name",
    quote_ticker="The quote currency's ticker name",
    price="The price that you are willing to pay for one currency",
    amount="How many do you want to buy"
)
async def trade_command(inter: discord.Interaction,
                        trade_type: str,
                        base_ticker: str,
                        quote_ticker: str,
                        price: str,
                        amount: str):
    try:
        await inter.response.defer(ephemeral=True)
        match trade_type.lower():
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
                f"> ## ❌Trade failed\n"
                f"> ### Reverse tickers are not supported yet.\n"
                f"> ### Please use {quote_ticker} as base and {base_ticker} as quote\n"

            )
            return
        if result[0] == 1:
            await inter.followup.send(
                f"> ## ✅{'Buy' if result[2] else 'Sell'} Order listed\n"
                f"> `Trade Number: {result[1]}`"
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
        await inter.followup.send("Something went wrong")
        raise e


@bot.tree.command(name="trade_cancel", description="Closes a trade")
@app_commands.describe(trade_number="The trade number when you list a trade")
async def close_trade(inter: discord.Interaction, trade_number: str):
    try:
        await inter.response.defer(ephemeral=True)
        result = await Currency.cancel_trade(inter.user.id, int(trade_number))
        if result == 0:
            await inter.followup.send(
                f"> ## Trade Order Closed"
            )
        else:
            await inter.followup.send(
                f"> ## Fail to Close trade\n"
                f"> ### Reasons:\n"
                f"> ### The Trade is not yours\n"
                f"> ### Maybe the trade was fulfilled already\n"
                f"> ### The trade didn't exist"
            )
    except Exception as e:
        await inter.followup.send("Something went wrong")
        raise e


@bot.tree.command(name="chart", description="Views the Chart of a market")
async def chart_command(inter: discord.Interaction, base_ticker: str, quote_ticker: str, scale: str, limit: int):
    try:
        await inter.response.defer(ephemeral=True)
        match scale.lower():
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
            case '1m':
                chosen_scale = ViewTrade.TimeScale.MONTH
            case _:
                await inter.followup.send(
                    "> ### Invalid scale input"
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
        await inter.followup.send(f"> # {base_ticker.upper()}/{quote_ticker.upper()}\n"
                                  f"> # {await Currency.last_trade_price(base_ticker, quote_ticker):,.4f} {quote_ticker.upper()}\n"
                                  f"> ## 🟩 Bid: {bid_ask[0]} | 🟥 Ask: {bid_ask[1]}\n"
                                  f"> ## Spread: {abs(bid_ask[0] - bid_ask[1])}",
                                  file=chart_image)

    except Exception as e:
        await inter.followup.send("Something went wrong")
        raise e


@bot.tree.command(name="mint", description="Creates new money (Prints more money)")
@app_commands.describe(amount="Amount that you want to mint")
async def mint_command(inter: discord.Interaction, amount: float):
    try:
        await inter.response.defer(ephemeral=True)
        if not NumberFormatter.validate_decimal_places(amount):
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
        inter.followup.send("Something went wrong")
        raise e


@bot.tree.command(name="burn", description="Burns money (Destroys money)")
@app_commands.describe(amount="Amount that you want to burn")
async def mint_command(inter: discord.Interaction, amount: float):
    try:
        await inter.response.defer(ephemeral=True)
        if not NumberFormatter.validate_decimal_places(amount):
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
                f"> ### Balance is less than 0.0001"
            )
        # elif result == -4:
        #     await inter.followup.send(
        #         f"> ## ⛔ Fail to burn\n"
        #         f"> ### Balance is greater than 999,999,999,999,999"
        #     )

    except Exception as e:
        inter.followup.send("Something went wrong")
        raise e


# @bot.tree.command(name="test", description="Debug")
# async def hello(interaction: discord.Interaction, base: int, quote: int):
#     result = await Currency.is_reverse_pair_exists(base, quote)
#     await interaction.response.send_message(f"{result}")


bot.run(properties['TOKEN'], log_handler=handler)
