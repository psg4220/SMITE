import enum
import json

import Boat
import Currency


class Action(enum.Enum):
    WITHDRAW = 0
    DEPOSIT = 1


class Provider(enum.Enum):
    UNBELIEVABOAT = 0


class BoatTransfer:

    def __init__(self, economy: Boat.Economy):
        self.economy = economy

    async def transfer(self, amount: int, action: Action):
        try:
            # Unbelievaboat account debited
            balance = self.economy.get_balance()
            boat_bank_balance = balance["bank"]
            currency_id = await Currency.get_currency_id(self.economy.guild_id, Currency.InputType.GUILD_ID.value)
            currency_ticker = await Currency.get_currency_ticker(currency_id, Currency.InputType.CURRENCY_ID.value)
            smite_balance = await Currency.view_balance(self.economy.user_id,
                                                        currency_ticker,
                                                        Currency.InputType.TICKER.value
                                                        )
            if (smite_balance - amount) < 0 and action == Action.DEPOSIT:
                return -1
            self.economy.update_balance(cash=0, bank=-amount if action == Action.WITHDRAW else amount)
            # SMITE account credited
            if currency_id is None:
                return -2
            if (boat_bank_balance - amount) < 0 and action == Action.WITHDRAW:
                return -1
            await Currency.edit_balance(self.economy.user_id,
                                        currency_id,
                                        amount,
                                        is_subtract=False if action == Action.WITHDRAW else amount)
            return 0
        except Exception as e:
            raise e
