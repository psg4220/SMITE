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
            # Retrieve Unbelievaboat balance
            balance = self.economy.get_balance()
            status_code = balance[1]
            if status_code >= 400:
                return -3

            boat_bank_balance = balance[0]["bank"]

            # Retrieve SMITE balance
            currency_id = await Currency.get_currency_id(self.economy.guild_id, Currency.InputType.GUILD_ID.value)
            currency_ticker = await Currency.get_currency_ticker(currency_id, Currency.InputType.CURRENCY_ID.value)
            smite_balance = await Currency.view_balance(
                self.economy.user_id,
                currency_ticker,
                Currency.InputType.TICKER.value
            )
            # Check if there are sufficient funds for the action
            if action == Action.DEPOSIT and (smite_balance - amount) < 0:
                return -1
            if action == Action.WITHDRAW and (boat_bank_balance - amount) < 0:
                return -1

            # Update Unbelievaboat balance
            new_balance = -amount if action == Action.WITHDRAW else amount
            status_code = self.economy.update_balance(cash=0, bank=new_balance)[1]
            if status_code >= 400:
                return -3

            # Update SMITE balance
            if currency_id is None:
                return -2

            await Currency.edit_balance(
                self.economy.user_id,
                currency_id,
                amount,
                is_subtract=(action == Action.DEPOSIT)
            )

            return 0
        except Exception as e:
            raise e

