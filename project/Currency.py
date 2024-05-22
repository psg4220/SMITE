import enum
import json
import uuid

import aiosqlite
import aiofiles

import Account
import Trading
import WireTransfer
import InputFormatter
from Account import AccountNumber
from Trading import Trade


class InputType(enum.Enum):
    CURRENCY_NAME = 0
    ACCOUNT_ID = 1
    TICKER = 2
    GUILD_ID = 3
    CURRENCY_ID = 4


async def get_connection():
    try:
        async with aiofiles.open('properties.json', 'r') as f:
            return await aiosqlite.connect(json.loads(await f.read())['SQLITE_PATH'])
    except Exception as e:
        raise e


async def create_tables():
    db = await get_connection()
    try:
        cursor = await db.cursor()
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS currencies(
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            ticker VARCHAR(4) NOT NULL CHECK(ticker GLOB '[A-Z]*'),
            guild_id INT
            )
            '''
        )
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS balance(
            id INTEGER PRIMARY KEY, 
            currency_id int NOT NULL, 
            user_discord_id int NOT NULL, 
            account_id BLOB NOT NULL, 
            balance DECIMAL(12,2) NOT NULL, 
            FOREIGN KEY(currency_id) REFERENCES currencies(id)
            )
            '''
        )
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS transactions(
            uuid blob NOT NULL,
            balance_sender_id int NOT NULL,
            balance_receiver_id int NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            transaction_date int NOT NULL,
            FOREIGN KEY (balance_sender_id) REFERENCES balance(id),
            FOREIGN KEY (balance_receiver_id) REFERENCES balance(id)
            )
            '''
        )
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS active_trades(
            id INTEGER PRIMARY KEY,
            user_discord_id int,
            trade_type int,
            base_currency_id int,
            quote_currency_id int,
            price DECIMAL(12,2),
            amount DECIMAL(12,2),
            FOREIGN KEY(base_currency_id) REFERENCES currencies(id),
            FOREIGN KEY(quote_currency_id) REFERENCES currencies(id)
            )   
            '''
        )
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS trade_log(
            id INTEGER PRIMARY KEY,
            base_currency_id int,
            quote_currency_id int,
            price DECIMAL(12,2),
            trade_date int,
            FOREIGN KEY(base_currency_id) REFERENCES currencies(id),
            FOREIGN KEY(quote_currency_id) REFERENCES currencies(id)
            )
            '''
        )
        await cursor.execute(
            '''
            CREATE TRIGGER IF NOT EXISTS update_balance
            AFTER INSERT ON transactions
            BEGIN
                UPDATE balance
                SET balance = balance - NEW.amount
                WHERE id = NEW.balance_sender_id;
            
                UPDATE balance
                SET balance = balance + NEW.amount
                WHERE id = NEW.balance_receiver_id;
            END;
            '''
        )
        await cursor.execute(
            '''
            CREATE VIEW IF NOT EXISTS transaction_summary AS 
            SELECT 
                t.uuid,
                c.name AS currency_name,
                MAX(CASE 
                    WHEN t.balance_sender_id = b.id THEN b.account_id
                    ELSE NULL
                END) AS account_id_sender,
                MAX(CASE 
                    WHEN t.balance_receiver_id = b.id THEN b.account_id
                    ELSE NULL
                END) AS account_id_receiver,
                MAX(t.amount) AS amount,
                MAX(t.transaction_date) AS transaction_date
            FROM 
                transactions AS t
            JOIN 
                balance AS b ON t.balance_sender_id = b.id OR t.balance_receiver_id = b.id
            JOIN 
                currencies AS c ON c.id = b.currency_id
            GROUP BY 
                t.uuid 
            ORDER BY 
                transaction_date DESC
            '''
        )
        await cursor.execute(
            '''
            CREATE VIEW IF NOT EXISTS active_trade_summary AS
            SELECT
                at.id,
                base_currency.ticker AS base_currency_ticker,
                quote_currency.ticker AS quote_currency_ticker,
                at.user_discord_id,
                CASE
                    WHEN at.trade_type = 0 THEN 'BUY'
                    WHEN at.trade_type = 1 THEN 'SELL'
                    ELSE NULL
                END AS trade_type,
                at.price,
                at.amount
            FROM
                active_trades AS at
            JOIN
                currencies AS base_currency ON at.base_currency_id = base_currency.id
            JOIN
                currencies AS quote_currency ON at.quote_currency_id = quote_currency.id;
            '''
        )
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS provider_auth(
                id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                provider_id INTEGER NOT NULL,
                auth_token TEXT
            )
            '''
        )
    except Exception as e:
        raise e
    finally:
        await db.close()


async def create_currency(discord_id: int, guild_id: int, name: str, ticker: str, initial_balance: float):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            is_limit = await is_currency_limit(discord_id)
            is_exist_name = await is_currency_exist(name)
            is_exist_ticker = await is_currency_exist(ticker, InputType.TICKER.value)
            if not is_limit or not is_exist_name or not is_exist_ticker:
                return -1
            await cursor.execute(
                '''
                INSERT INTO currencies(name,ticker) 
                VALUES (?,?)
                ''',
                (name, ticker.upper())
            )
            currency_id = cursor.lastrowid

            await cursor.execute(
                '''
                INSERT INTO balance(currency_id,user_discord_id,account_id,balance) 
                VALUES (?,?,?,?)
                ''',
                (currency_id, int(discord_id), Account.to_bytes(await generate_account_id(discord_id)), initial_balance)
            )
            balance_id = cursor.lastrowid
            await cursor.execute(
                '''
                INSERT INTO transactions(
                uuid,
                balance_sender_id,
                balance_receiver_id,
                amount,
                transaction_date
                )
                VALUES (?,?,?,?,strftime('%s', 'now'))
                ''',
                (uuid.uuid4().bytes, balance_id, balance_id, initial_balance)
            )
            result = await set_currency_guild_id(discord_id, guild_id)
            if result == -1:
                await db.rollback()
                return -2
        await db.commit()
        return 0
    except Exception as e:
        await db.rollback()
        await db.close()
        raise e
    finally:
        await db.close()


async def has_currency(guild_id: int):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT
                    COUNT(*)
                FROM
                    currencies
                WHERE
                    guild_id = ?
                ''',
                (guild_id,)
            )
            count = await cursor.fetchone()
            if count[0] > 0:
                return True
            return False
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def set_currency_guild_id(discord_id: int, guild_id: int):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            if await has_currency(guild_id):
                return -1
            central_account = await get_central_account(discord_id, is_discord_id=True)
            if central_account is None:
                return -2
            await cursor.execute(
                '''
                UPDATE
                    currencies
                SET
                    guild_id = ?
                WHERE
                    id = ?
                ''',
                (
                    guild_id,
                    central_account[6]
                )
            )
            await db.commit()
            return 0
    except Exception as e:
        await db.rollback()
        raise e
    finally:
        await db.close()


async def unset_currency_guild_id(discord_id: int):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            central_account = await get_central_account(discord_id, is_discord_id=True)
            if central_account is None:
                return -1
            await cursor.execute(
                '''
                UPDATE
                    currencies
                SET
                    guild_id = NULL
                WHERE
                    id = ?
                ''',
                (
                    central_account[6],
                )
            )
            await db.commit()
            return 0
    except Exception as e:
        await db.rollback()
        raise e
    finally:
        await db.close()


async def generate_account_id(discord_id: int):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT id, currency_id FROM balance 
                ORDER BY id DESC
                LIMIT 1
                '''
            )
            result = await cursor.fetchone()
            if result is None:
                return AccountNumber(1, 1, discord_id).generate()
            account = AccountNumber(result[0], result[1], discord_id)
            return account.generate()
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_account_id(discord_id: int, search: str, find_by=0):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            if find_by == 0:
                column_name = 'c.name'
            elif find_by == 2:
                column_name = 'c.ticker'
                search = search.upper()
            else:
                return None
            if not await is_balance_exist(discord_id, search, find_by):
                acn = await create_address(discord_id, search, find_by)
                if acn is None:
                    return None
                return Account.from_bytes(acn)
            await cursor.execute(
                f'''
                SELECT account_id FROM currencies AS c 
                INNER JOIN balance as b ON b.currency_id = c.id 
                WHERE {column_name} = ? AND b.user_discord_id = ?
                ''',
                (search, discord_id)
            )
            acn_bytes = await cursor.fetchone()
            if acn_bytes is None:
                return None
            return Account.from_bytes(acn_bytes[0])
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def is_currency_limit(discord_id: int, limit=1):
    db = await get_connection()
    try:
        cursor = await db.cursor()
        await cursor.execute(
            '''
            SELECT COUNT(*) FROM currencies AS c
            INNER JOIN balance AS b ON b.currency_id = c.id
            INNER JOIN transactions AS t ON t.balance_sender_id = b.id AND t.balance_receiver_id = b.id
            WHERE b.user_discord_id = ?
            ''',
            (discord_id,)
        )
        count = await cursor.fetchone()
        if count is None:
            return True
        else:
            return count[0] < limit
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def is_currency_exist(search: str, find_by=0):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            match find_by:
                case 0:
                    column_name = 'name'
                case 2:
                    column_name = 'ticker'
                case _:
                    return False
            await cursor.execute(
                f'''
                SELECT COUNT(*) FROM currencies 
                WHERE {column_name} = ?
                ''',
                (search,)
            )
            count = await cursor.fetchone()
            if count is None:
                return False
            return count[0] == 0
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def transfer(discord_id: int, acn_receiver: str, amount: float):
    if amount <= 0:
        return -1
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            acn_receiver_bytes = Account.to_bytes(acn_receiver)
            await cursor.execute(
                '''
                SELECT id,currency_id FROM balance AS b 
                WHERE account_id = ?
                ''',
                (acn_receiver_bytes,)
            )
            receiver = await cursor.fetchone()
            if receiver is None:
                return -2
            await cursor.execute(
                '''
                SELECT id,b.balance,account_id FROM balance AS b 
                WHERE currency_id = ? 
                AND user_discord_id = ?
                ''',
                (receiver[1], discord_id)
            )
            sender = await cursor.fetchone()
            if sender is None:
                return -3
            if sender[1] < amount:
                return -4
            if sender[2] == acn_receiver_bytes:
                return -5
            transaction_id = uuid.uuid4()
            await cursor.execute(
                '''
                INSERT INTO transactions(uuid,balance_sender_id,balance_receiver_id,amount,transaction_date) 
                VALUES (?,?,?,?,strftime('%s', 'now'))
                ''',
                (transaction_id.bytes, sender[0], receiver[0], amount)
            )
            await db.commit()
            return transaction_id, \
                await get_discord_id(acn_receiver), \
                await get_currency_name(acn_receiver, find_by=InputType.ACCOUNT_ID.value), \
                await get_currency_ticker(acn_receiver, find_by=InputType.ACCOUNT_ID.value)
    except Exception as e:
        await db.rollback()
        await db.close()
        raise e
    finally:
        await db.close()


async def get_discord_id(acn: str):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT user_discord_id 
                FROM balance 
                WHERE 
                account_id = ?
                ''',
                (Account.to_bytes(acn),)
            )
            discord_id = await cursor.fetchone()
            if discord_id is None:
                return None
            return discord_id[0]
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_currency_ticker(search, find_by=0):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            if find_by == 0:
                column_name = 'c.name'
            elif find_by == 1:
                column_name = 'b.account_id'
                search = Account.to_bytes(search)
            elif find_by == 4:
                column_name = "c.id"
            else:
                return None
            await cursor.execute(
                f'''
                SELECT 
                c.ticker 
                FROM 
                currencies AS c 
                INNER JOIN balance AS b 
                ON c.id = b.currency_id 
                WHERE 
                {column_name} = ?
                ''',
                (search,)
            )
            currency_id = await cursor.fetchone()
            if currency_id is None:
                return None
            return currency_id[0]
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_currency_name(search: str, find_by=1):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            if find_by == InputType.ACCOUNT_ID.value:
                column_name = 'b.account_id'
                search = Account.to_bytes(search)
            elif find_by == InputType.TICKER.value:
                column_name = 'c.ticker'
                search = search.upper()
            else:
                return None
            await cursor.execute(
                f'''
                SELECT 
                c.name 
                FROM 
                currencies AS c 
                INNER JOIN balance AS b 
                ON c.id = b.currency_id 
                WHERE 
                {column_name} = ?
                LIMIT 1
                ''',
                (search,)
            )
            currency_id = await cursor.fetchone()
            if currency_id is None:
                return None
            return currency_id[0]
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_currency_id(search, find_by=0):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            if find_by == 0:
                column_name = 'c.name'
            elif find_by == 1:
                column_name = 'b.account_id'
                search = Account.to_bytes(search)
            elif find_by == 2:
                column_name = 'c.ticker'
                search = search.upper()
            elif find_by == 3:
                column_name = 'c.guild_id'
            else:
                return None
            await cursor.execute(
                f'''
                SELECT 
                c.id 
                FROM 
                currencies AS c 
                INNER JOIN balance AS b 
                ON c.id = b.currency_id 
                WHERE 
                {column_name} = ?
                LIMIT 1
                ''',
                (search,)
            )
            currency_id = await cursor.fetchone()
            if currency_id is None:
                return None
            return currency_id[0]
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def is_balance_exist(discord_id: int, search: str, find_by=0):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            match find_by:
                case 0:
                    column_name = 'c.name'
                case 1:
                    column_name = 'b.account_id'
                    search = Account.to_bytes(search)
                case 2:
                    column_name = 'c.ticker'
                    search = search.upper()
            await cursor.execute(
                f'''
                SELECT COUNT(*) 
                FROM
                balance AS b 
                INNER JOIN currencies AS c 
                ON b.currency_id = c.id  
                WHERE 
                {column_name} = ? 
                AND b.user_discord_id = ?
                ''',
                (search, discord_id)
            )
            count = await cursor.fetchone()
            if count is None:
                return False
            return count[0] > 0
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def create_address(discord_id: int, search: str, find_by=0):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            currency_id = await get_currency_id(search, find_by)
            if currency_id is None:
                return None
            acn_bytes = Account.to_bytes(await generate_account_id(discord_id))
            await cursor.execute(
                '''
                INSERT INTO balance(currency_id,user_discord_id,account_id,balance) 
                VALUES (?,?,?,?)
                ''',
                (currency_id, discord_id, acn_bytes, 0)
            )
            await db.commit()
            return acn_bytes
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def view_balance(discord_id: int, search: str, find_by=0):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            if not await is_balance_exist(discord_id, search, find_by):
                await create_address(discord_id, search, find_by)
            await cursor.execute(
                '''
                SELECT b.balance FROM balance AS b
                WHERE user_discord_id = ? 
                AND currency_id = ?
                ''',
                (discord_id, await get_currency_id(search, find_by=find_by))
            )
            balance = await cursor.fetchone()
            if balance is None:
                return None
            return balance[0]
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def is_central(acn: str):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT id FROM balance 
                WHERE account_id = ?
                ''',
                (Account.to_bytes(acn),)
            )
            balance_id = await cursor.fetchone()
            if balance_id is None:
                return False
            await cursor.execute(
                '''
                SELECT COUNT(*) FROM transactions 
                WHERE balance_sender_id = ? 
                AND balance_receiver_id = ? 
                ORDER BY transaction_date ASC
                LIMIT 1
                ''',
                (balance_id[0], balance_id[0])
            )
            count = await cursor.fetchone()
            if count is None:
                return False
            return count[0] > 0
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_transaction_info(transaction_uuid: str):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT 
                *
                FROM 
                transaction_summary
                WHERE 
                uuid = ?
                ''',
                (uuid.UUID(transaction_uuid).bytes,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return row
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_balance_id(discord_id: int, currency_id: int):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT id 
                FROM balance 
                WHERE user_discord_id = ? 
                AND currency_id = ? 
                ''',
                (discord_id, currency_id)
            )
            balance_id = await cursor.fetchone()
            if balance_id is None:
                return None
            return balance_id[0]
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_active_trades_supply(currency_id: int):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT
                    SUM(amount)
                FROM
                    active_trades   
                WHERE
                    base_currency_id = ?
                    AND trade_type = 1
                ''',
                (
                    currency_id,
                )
            )
            sell_worth = await cursor.fetchone()
            if sell_worth is None:
                return None
            if sell_worth[0] is None:
                sell_worth = [0]
            await cursor.execute(
                '''
                SELECT
                    SUM(amount)
                FROM
                    active_trades
                WHERE
                    base_currency_id = ?
                    AND trade_type = 0
                ''',
                (
                    currency_id,
                )
            )
            buy_worth = await cursor.fetchone()
            if buy_worth is None:
                return None
            if buy_worth[0] is None:
                buy_worth = [0]
            return sell_worth[0] + buy_worth[0]
    except Exception as e:
        raise e
    finally:
        await db.close()


async def get_central_account(unique_id: int, is_discord_id=False):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            if is_discord_id:
                column_name = "user_discord_id"
            else:
                column_name = "currency_id"
            await cursor.execute(
                f'''
                SELECT
                    *
                FROM
                    transactions AS t
                INNER JOIN
                    balance AS b
                ON
                    b.id = t.balance_sender_id
                    AND b.id = t.balance_receiver_id
                WHERE
                    {column_name} = ?
                ORDER BY
                    t.transaction_date ASC
                LIMIT 1
                ''',
                (unique_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return row
    except Exception as e:
        raise e
    finally:
        await db.close()


async def get_reserve_supply(currency_id: int):
    try:
        row = await get_central_account(currency_id)
        return row[9]
    except Exception as e:
        raise e


async def get_central_date_creation(currency_id: int):
    try:
        row = await get_central_account(currency_id)
        return row[4]
    except Exception as e:
        raise e


async def get_maximum_supply(currency_id: int):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT
                    SUM(balance)
                FROM
                    balance
                WHERE
                    currency_id = ?
                ''',
                (currency_id,)
            )
            max_supply = await cursor.fetchone()
            if max_supply is None:
                return None
            return max_supply[0]
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def trade(discord_id, user_trade: Trade):
    db = await get_connection()
    is_buy = user_trade.trade_type == Trading.TradeType.BUY
    try:
        async with db.cursor() as cursor:
            base_currency_id = await get_currency_id(user_trade.base_ticker, InputType.TICKER.value)
            quote_currency_id = await get_currency_id(user_trade.quote_ticker, InputType.TICKER.value)

            # Checks if the user have a balance. If there is none then create one
            # P.S. This shit is now confusing for me. so base and quote are checked just in case.
            if not await is_balance_exist(discord_id, user_trade.quote_ticker, InputType.TICKER.value):
                await create_address(discord_id, user_trade.quote_ticker, InputType.TICKER.value)
            if not await is_balance_exist(discord_id, user_trade.base_ticker, InputType.TICKER.value):
                await create_address(discord_id, user_trade.base_ticker, InputType.TICKER.value)

            # Checks if the funds are enough
            if is_buy:
                buyer_balance = await view_balance(discord_id, user_trade.quote_ticker, InputType.TICKER.value)
                if buyer_balance is None or buyer_balance < user_trade.total():
                    return -1
            else:
                seller_balance = await view_balance(discord_id, user_trade.base_ticker, InputType.TICKER.value)
                if seller_balance is None or seller_balance < user_trade.amount:
                    return -1

            # If base or quote currency is none then return an error:
            if base_currency_id is None or quote_currency_id is None:
                return -2

            # Searches for active_trades greater than equal the amount
            await cursor.execute(
                '''
                SELECT
                * 
                FROM
                active_trades
                WHERE 
                trade_type = ?
                AND base_currency_id = ?
                AND quote_currency_id = ?
                AND price = ?
                AND amount >= ? 
                AND NOT user_discord_id = ?
                ORDER BY amount ASC
                LIMIT 1
                ''',
                (
                    Trading.TradeType.SELL.value
                    if user_trade.trade_type is Trading.TradeType.BUY
                    else Trading.TradeType.BUY.value,
                    base_currency_id,
                    quote_currency_id,
                    user_trade.price,
                    user_trade.amount,
                    discord_id
                )
            )
            selected_trade = await cursor.fetchone()
            # if there is no match. list the trade from active trades
            if selected_trade is None:
                await cursor.execute(
                    '''
                    INSERT INTO active_trades(
                    user_discord_id,
                    trade_type,
                    base_currency_id,
                    quote_currency_id,
                    price,
                    amount
                    ) 
                    VALUES(?,?,?,?,?,?)
                    ''',
                    (
                        discord_id,
                        user_trade.trade_type.value,
                        base_currency_id,
                        quote_currency_id,
                        user_trade.price,
                        user_trade.amount
                    )

                )
                # Subtract balance since you listed it
                if is_buy:
                    await edit_balance_on_connection(cursor,
                                                     discord_id,
                                                     quote_currency_id,
                                                     user_trade.total(),
                                                     is_subtract=True)
                else:
                    await edit_balance_on_connection(cursor,
                                                     discord_id,
                                                     base_currency_id,
                                                     user_trade.amount,
                                                     is_subtract=True)
                await db.commit()
                return 1, cursor.lastrowid, is_buy
            else:
                subtracted_amount = float(selected_trade[6]) - user_trade.amount
                is_fulfilled = False
                # Delete the trade if the amount is zero since it is now finished
                if subtracted_amount <= 0:
                    await cursor.execute(
                        '''
                        DELETE FROM
                            active_trades
                        WHERE
                            id = ?
                        ''',
                        (
                            int(selected_trade[0]),
                        )
                    )
                    is_fulfilled = True
                else:
                    await cursor.execute(
                        '''
                        UPDATE
                            active_trades
                        SET
                            amount = ?
                        WHERE
                            id = ?
                        ''',
                        (
                            subtracted_amount,
                            int(selected_trade[0])
                        )
                    )
                # This updates the balance
                # P.S. This has now become a clusterfuck. I think there is alternative to this, but
                # I will let it for now, (band aid solution)
                if is_buy:
                    await edit_balance_on_connection(
                        cursor,
                        discord_id,
                        quote_currency_id,
                        user_trade.total(),
                        is_subtract=True
                    )
                    await edit_balance_on_connection(
                        cursor,
                        discord_id,
                        base_currency_id,
                        user_trade.amount
                    )
                    await edit_balance_on_connection(
                        cursor,
                        selected_trade[1],
                        quote_currency_id,
                        user_trade.total()
                    )
                else:
                    await edit_balance_on_connection(
                        cursor,
                        selected_trade[1],
                        base_currency_id,
                        user_trade.amount
                    )
                    await edit_balance_on_connection(
                        cursor,
                        discord_id,
                        base_currency_id,
                        user_trade.amount,
                        is_subtract=True
                    )
                    await edit_balance_on_connection(
                        cursor,
                        discord_id,
                        quote_currency_id,
                        user_trade.total()
                    )
                # Logs the trade into trade_log for the chart
                await log_trade(
                    db,
                    base_currency_id,
                    quote_currency_id,
                    user_trade.price
                )
                await db.commit()
                return 0, selected_trade[1], selected_trade[0], is_fulfilled
    except Exception as e:
        await db.rollback()
        await db.close()
        raise e
    finally:
        await db.close()


async def cancel_trade(discord_id: int, trade_id: int):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT * FROM active_trades WHERE id = ?
                ''',
                (
                    trade_id,
                )
            )
            selected_trade = await cursor.fetchone()
            if selected_trade is None:
                return -1
            if not selected_trade[1] == discord_id:
                return -2
            base_currency_id = selected_trade[3]
            quote_currency_id = selected_trade[4]
            price = selected_trade[5]
            amount = selected_trade[6]
            is_buy = selected_trade[2] == Trading.TradeType.BUY.value
            if is_buy:
                await edit_balance_on_connection(
                    cursor,
                    discord_id,
                    quote_currency_id,
                    price * amount
                )
            else:
                await edit_balance_on_connection(
                    cursor,
                    discord_id,
                    base_currency_id,
                    amount
                )
            await cursor.execute(
                '''
                DELETE FROM active_trades WHERE id = ?
                ''',
                (trade_id,)
            )
            await db.commit()
            return 0
    except Exception as e:
        await db.rollback()
        await db.close()
        raise e
    finally:
        await db.close()


async def edit_balance(discord_id: int, currency_id: int, amount, is_subtract=False):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                f'''
                UPDATE
                    balance
                SET
                    balance = balance {'-' if is_subtract else '+'} ?
                WHERE
                    user_discord_id = ?
                    AND currency_id = ?
                ''',
                (amount, discord_id, currency_id)
            )
            await db.commit()
    except Exception as e:
        await db.rollback()
        await db.close()
        raise e
    finally:
        await db.close()


async def edit_balance_on_connection(cursor, discord_id: int, currency_id: int, amount, is_subtract=False):
    try:
        await cursor.execute(
            f'''
            UPDATE
                balance
            SET
                balance = balance {'-' if is_subtract else '+'} ?
            WHERE
                user_discord_id = ?
                AND currency_id = ?
            ''',
            (amount, discord_id, currency_id)
        )
    except Exception as e:
        raise e


async def is_reverse_pair_exists(db, base_currency_id, quote_currency_id):
    async with db.cursor() as cursor:
        # Prepare the query to check for both the original and reversed currency pair
        await cursor.execute(
            '''
            SELECT base_currency_id, quote_currency_id
            FROM active_trades
            WHERE 
                (base_currency_id = ? AND quote_currency_id = ?)
                OR
                (base_currency_id = ? AND quote_currency_id = ?)
            LIMIT 1
            ''',
            (base_currency_id, quote_currency_id, quote_currency_id, base_currency_id)
        )
        result = await cursor.fetchone()
        if result is None:
            return None
        if result[0] == quote_currency_id and result[1] == base_currency_id:
            return True
        else:
            return False


async def log_trade(cursor, base_currency_id: int, quote_currency_id: int, price: float):
    try:
        await cursor.execute(
            '''
            INSERT INTO
                trade_log 
            (
                base_currency_id,
                quote_currency_id,
                price,
                trade_date
            ) 
            VALUES 
            (?,?,?,strftime('%s', 'now'))
            ''',
            (
                base_currency_id,
                quote_currency_id,
                price
            )
        )
    except Exception as e:
        raise e


async def last_trade_price(base_ticker, quote_ticker):
    base_currency_id = await get_currency_id(base_ticker, InputType.TICKER.value)
    quote_currency_id = await get_currency_id(quote_ticker, InputType.TICKER.value)
    try:
        db = await get_connection()
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT
                    price
                FROM
                    trade_log
                WHERE
                    base_currency_id = ?
                    AND quote_currency_id = ?
                ORDER BY 
                    trade_date DESC 
                LIMIT 1
                ''',
                (
                    base_currency_id,
                    quote_currency_id
                )
            )
            price = await cursor.fetchone()
            if price is None:
                return None
            return price[0]
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_bid_ask_price(base_ticker, quote_ticker):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            base_currency_id = await get_currency_id(base_ticker, InputType.TICKER.value)
            quote_currency_id = await get_currency_id(quote_ticker, InputType.TICKER.value)
            await cursor.execute(
                '''
                SELECT
                    MAX(price)
                FROM
                    active_trades
                WHERE
                    base_currency_id = ?
                    AND quote_currency_id = ?
                    AND trade_type = 0
                ''',
                (base_currency_id, quote_currency_id)
            )
            bid_price = await cursor.fetchone()
            await cursor.execute(
                '''
                SELECT
                    MIN(price)
                FROM
                    active_trades
                WHERE
                    base_currency_id = ?
                    AND quote_currency_id = ?
                    AND trade_type = 1
                ''',
                (base_currency_id, quote_currency_id)
            )
            ask_price = await cursor.fetchone()
            if bid_price is not None:
                bid_price = bid_price[0]
            if ask_price is not None:
                ask_price = ask_price[0]
            return bid_price, ask_price
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def mint_currency(discord_id: int, amount: float, is_subtract=False):
    if amount < 0.0001:
        return -1
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT
                    b.id,
                    b.balance
                FROM
                    transactions AS t
                INNER JOIN 
                    balance AS b 
                ON 
                    b.id = t.balance_sender_id
                    AND b.id = t.balance_receiver_id
                WHERE
                    b.user_discord_id = ?
                ORDER BY
                    t.transaction_date ASC
                LIMIT 1
                ''',
                (
                    discord_id,
                )
            )
            row = await cursor.fetchone()
            if row is None:
                return -2
            if is_subtract:
                new_balance = row[1] - amount
                if new_balance < 0:
                    return -3
            else:
                new_balance = row[1] + amount
                if new_balance > 999_999_999_999_999:
                    return -4
            await cursor.execute(
                '''
                UPDATE
                    balance
                SET
                    balance = ?
                WHERE 
                    id = ?
                ''',
                (
                    new_balance,
                    row[0]
                )
            )
            await db.commit()
            return 0
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def is_authorized_user(discord_id: int, guild_id: int):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT
                    id
                FROM
                    currencies
                WHERE
                    guild_id = ?
                ''',
                (guild_id,)
            )
            currency_id = await cursor.fetchone()
            if currency_id is None:
                return False
            central_account = await get_central_account(discord_id, is_discord_id=True)
            if central_account is None:
                return False
            if central_account[6] != currency_id[0]:
                return False
            return True

    except Exception as e:
        raise e
    finally:
        await db.close()


async def create_provider_auth(discord_id: int, guild_id: int, provider: WireTransfer.Provider, auth_token: str):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT
                    COUNT(*)
                FROM
                    provider_auth
                WHERE
                    guild_id = ?
                    AND provider_id = ?
                ''',
                (guild_id, provider.value)
            )
            count = await cursor.fetchone()
            if count[0] > 0:
                return -1
            central_account = await get_central_account(discord_id, is_discord_id=True)
            if central_account is None:
                return -2
            if discord_id != central_account[7]:
                return -2
            await cursor.execute(
                '''
                INSERT INTO provider_auth(provider_id, guild_id, auth_token) VALUES (?,?,?)
                ''',
                (provider.value, guild_id, auth_token)
            )
            await db.commit()
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def set_provider_auth(discord_id: int, guild_id: int, provider: WireTransfer.Provider, auth_token: str):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            central_account = await get_central_account(discord_id, is_discord_id=True)
            if central_account is None:
                return -1
            if discord_id != central_account[7]:
                return -1
            await cursor.execute(
                '''
                UPDATE
                provider_auth
                SET
                auth_token = ?
                WHERE
                guild_id = ?
                AND provider_id = ?
                ''',
                (
                    auth_token,
                    guild_id,
                    provider.value
                )
            )
            await db.commit()
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def delete_provider_auth(guild_id: int, provider: WireTransfer.Provider):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                DELETE FROM provider_auth WHERE guild_id = ? AND provider_id = ?
                ''',
                (
                    guild_id,
                    provider.value
                )
            )
            await db.commit()
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_provider_auth(guild_id: int, provider: WireTransfer.Provider):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                '''
                SELECT
                    auth_token
                FROM
                    provider_auth
                WHERE
                    guild_id = ?
                    AND provider_id = ?
                ''',
                (
                    guild_id,
                    provider.value
                )
            )
            auth_token = await cursor.fetchone()
            if auth_token is None:
                return None
            return auth_token[0]
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def get_currencies(limit=10,page=1, show_last=False):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                f'''
                SELECT 
                    ticker, name 
                FROM 
                    currencies 
                ORDER BY 
                    id {"DESC" if show_last else "ASC"} 
                LIMIT {limit} 
                OFFSET {(page-1) * limit}
                '''
            )
            currencies = await cursor.fetchall()
            if currencies is None:
                return -1
            return currencies
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()


async def update_currency(guild_id: int, new_name: str, new_ticker: str):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            if await is_currency_exist(new_ticker, InputType.TICKER.value)\
                    or await is_currency_exist(new_name, InputType.CURRENCY_NAME.value):
                return -1
            new_ticker = new_ticker.upper()
            await cursor.execute(
                f'''
                UPDATE
                    currencies
                SET
                    name = ?,
                    ticker = ?
                WHERE
                    guild_id = ?
                ''',
                (
                    new_name,
                    new_ticker,
                    guild_id
                )
            )
            await db.commit()
    except Exception as e:
        await db.rollback()
        await db.close()
        raise e
    finally:
        await db.close()


async def trade_list(base_currency_ticker: str,
                     quote_currency_ticker: str,
                     trade_type: str,
                     page: int = 1,
                     limit: int = 10
                     ):
    db = await get_connection()
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                f'''
                SELECT 
                    id, 
                    base_currency_ticker || '/' || quote_currency_ticker AS pair, 
                    trade_type, 
                    price, 
                    amount
                FROM 
                    active_trade_summary
                WHERE
                    base_currency_ticker = ?
                    AND quote_currency_ticker = ?
                    AND trade_type = ?
                ORDER BY
                    price {'DESC' if trade_type == 'BUY' else 'ASC'}
                LIMIT ?
                OFFSET ?
                ''',
                (
                    base_currency_ticker,
                    quote_currency_ticker,
                    trade_type,
                    limit,
                    page-1 * limit
                )
            )
            trades = await cursor.fetchall()
            if not trades:
                return -1
            return trades
    except Exception as e:
        await db.close()
        raise e
    finally:
        await db.close()