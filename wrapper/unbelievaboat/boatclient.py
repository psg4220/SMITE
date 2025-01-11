import aiohttp

class BoatClient:

    @staticmethod
    async def get_balance(guild_id: int, discord_id: int, auth_token: str):
        url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}/users/{discord_id}"
        headers = {
            "accept": "application/json",
            "Authorization": f"{auth_token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                return data

    @staticmethod
    async def update_balance(amount: int, guild_id: int, discord_id: int, auth_token: str):
        url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}/users/{discord_id}"
        payload = {
            "bank": amount
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"{auth_token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=payload) as response:
                data = await response.json()
                return data