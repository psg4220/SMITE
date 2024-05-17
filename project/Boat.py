import os
import json

import requests


def get_auth():
    if os.path.exists('properties.json'):
        with open("properties.json", "r") as f:
            properties = json.load(f)
            return properties["BOAT_AUTH"]
    else:
        raise FileNotFoundError("properties.json doesn't exist")


def get_guild(guild_id: int):
    url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}"
    headers = {
        "accept": "application/json",
        "Authorization": get_auth()
    }
    response = requests.get(url, headers=headers)
    return response.json()


class Economy:

    def __init__(self, user_id: int, guild_id: int):
        self.user_id = user_id
        self.guild_id = guild_id
        self.auth = get_auth()

    def get_balance(self):
        url = f'https://unbelievaboat.com/api/v1/guilds/{self.guild_id}/users/{self.user_id}'
        headers = {
            "accept": "application/json",
            "Authorization": self.auth
        }
        response = requests.get(url, headers=headers)
        return response.json()

    def set_balance(self, cash: int, bank: int):
        url = f"https://unbelievaboat.com/api/v1/guilds/{self.guild_id}/users/{self.user_id}"
        payload = {
            "cash": cash,
            "bank": bank,
            "reason": f"set_balance in user_id: {self.user_id}\nCash: {cash}\nBank: {bank}"
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": self.auth
        }
        response = requests.put(url, json=payload, headers=headers)
        return response.json()

    def update_balance(self, cash=0, bank=0):
        url = f"https://unbelievaboat.com/api/v1/guilds/{self.guild_id}/users/{self.user_id}"
        payload = {
            "cash": cash,
            "bank": bank,
            "reason": f"update_balance in user_id: {self.user_id}\nCash: {cash}\nBank: {bank}"
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": self.auth
        }
        response = requests.patch(url, json=payload, headers=headers)
        return response.json()
