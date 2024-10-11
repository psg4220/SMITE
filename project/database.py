import enum
import aiosqlite
import aiofiles
import json


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
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS bank(
            id INTEGER PRIMARY KEY,
            name VARCHAR(50),
            currency_id INTEGER NOT NULL,
            date_created INTEGER NOT NULL,
            is_closed BOOL,
            FOREIGN KEY(currency_id) REFERENCES currencies(id)
            )
            '''
        )
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS bank_accounts(
                id INTEGER PRIMARY KEY,
                bank_id INTEGER NOT NULL,
                owner_discord_id INTEGER NOT NULL,
                balance INTEGER NOT NULL,
                status INTEGER
            )
            '''
        )
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS bonds(
                id INTEGER PRIMARY KEY,
                name VARCHAR(50),
                owner_bank_id INTEGER NOT NULL,
                currency_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                interest INTEGER NOT NULL,
                date_created INTEGER NOT NULL,
                due_date INTEGER NOT NULL,
                FOREIGN KEY(currency_id) REFERENCES currencies(id)
                )
            '''
        )
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS loans(
            id INTEGER PRIMARY KEY,
            amount INTEGER NOT NULL,
            interest INTEGER NOT NULL,
            lender_bank_acc_id INTEGER NOT NULL,
            borrower_bank_acc_id INTEGER NOT NULL,
            date_created INTEGER NOT NULL,
            due_date INTEGER NOT NULL,
            renew_fee INTEGER NOT NULL,
            status INTEGER NOT NULL,
            FOREIGN KEY(lender_bank_acc_id) REFERENCES bank_accounts(id),
            FOREIGN KEY(borrower_bank_acc_id) REFERENCES bank_accounts(id)
            )
            '''
        )
    except Exception as e:
        raise e
    finally:
        await db.close()
