from services.currencyservice import CurrencyService
from services.accountservice import AccountService
from services.transactionservice import TransactionService, Transaction
from services.tradeservice import TradeService, TradeType
import asyncio
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from services.tradelogservice import TradeLogService
from services.roleservice import RoleService
import random


async def populate_currencies():
    await CurrencyService.create_currency("LOLCoin", "LOL")
    await CurrencyService.create_currency("Darkcoin", "DRK")


async def populate_accounts():
    await AccountService.create_account(1234, 1, Decimal(1000))
    await AccountService.create_account(1234, 2, Decimal(0))

    await AccountService.create_account(5678, 1, Decimal(0))
    await AccountService.create_account(5678, 2, Decimal(1000))


async def main():
    base_currency_id = 7
    quote_currency_id = 8
    # current_date = datetime.now(timezone.utc)
    #
    # for i in range(10):
    #     # Create trade log using the service function
    #     await TradeLogService.create_trade_log(
    #         base_currency_id=base_currency_id,
    #         quote_currency_id=quote_currency_id,
    #         price=i
    #     )
    # trades = await TradeService.get_all_trades(limit=2, page=2)
    #
    # for t in trades:
    #     print(
    #         f"Discord ID: {t.discord_id}\n"
    #         f"Price: {t.price_offered}\n"
    #         f"Amount: {t.amount}\n"
    #     )
    # trade = await TradeService.process_trade(
    #     discord_id=1234,
    #     base_currency_id=base_currency_id,
    #     quote_currency_id=quote_currency_id,
    #     trade_type=TradeType.SELL,
    #     price=Decimal(2),
    #     amount=Decimal(500)
    # )
    # print(trade)
    # trade = await TradeService.process_trade(
    #     discord_id=1234,
    #     base_currency_id=base_currency_id,
    #     quote_currency_id=quote_currency_id,
    #     trade_type=TradeType.SELL,
    #     price=Decimal(1),
    #     amount=Decimal(1000)
    # )
    # print(trade)
    trade = await TradeService.process_trade(
        discord_id=5678,
        base_currency_id=7,
        quote_currency_id=8,
        trade_type=TradeType.BUY,
        price=Decimal(1),
        amount=Decimal(1000)
    )
    print(trade)

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
