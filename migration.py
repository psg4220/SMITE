import sqlite3
import pymysql
from datetime import datetime

def migrate_sqlite_to_mysql(sqlite_file, mysql_config):
    """
    Migrate data from an SQLite database to a MySQL database using raw SQL.

    :param sqlite_file: Path to the SQLite database file.
    :param mysql_config: Dictionary with MySQL connection parameters: host, user, password, database.
    """
    try:
        # Connect to SQLite database
        sqlite_conn = sqlite3.connect(sqlite_file)
        sqlite_cursor = sqlite_conn.cursor()

        # Connect to MySQL database
        mysql_conn = pymysql.connect(
            host=mysql_config['host'],
            user=mysql_config['user'],
            port=mysql_config['port'],
            password=mysql_config['password'],
            database=mysql_config['database']
        )
        mysql_cursor = mysql_conn.cursor()

        # Migrate currencies to currency
        sqlite_cursor.execute("SELECT id, name, ticker FROM currencies")
        currencies = sqlite_cursor.fetchall()

        for currency in currencies:
            currency_id, name, ticker = currency
            mysql_cursor.execute(
                "INSERT INTO currency (currency_id, name, ticker) VALUES (%s, %s, %s)",
                (currency_id, name, ticker)
            )

        # Migrate balance to account
        sqlite_cursor.execute("SELECT id, user_discord_id, currency_id, balance FROM balance")
        accounts = sqlite_cursor.fetchall()

        for account in accounts:
            account_id, discord_id, currency_id, balance = account
            mysql_cursor.execute(
                "INSERT INTO account (account_id, discord_id, currency_id, balance) VALUES (%s, %s, %s, %s)",
                (account_id, discord_id, currency_id, balance)
            )

        # Migrate active_trades to trade_list
        sqlite_cursor.execute(
            "SELECT id, user_discord_id, trade_type, base_currency_id, quote_currency_id, price, amount FROM active_trades"
        )
        active_trades = sqlite_cursor.fetchall()

        for trade in active_trades:
            trade_id, discord_id, trade_type, base_currency_id, quote_currency_id, price, amount = trade
            trade_type_str = 'BUY' if trade_type == 0 else 'SELL'
            mysql_cursor.execute(
                """
                INSERT INTO trade_list (trade_id, discord_id, base_currency_id, quote_currency_id, type, price_offered, amount, order_type, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (trade_id, discord_id, base_currency_id, quote_currency_id, trade_type_str, price, amount, 'LIMIT', 'OPEN')
            )

        # Migrate trade_log to trade_log
        sqlite_cursor.execute(
            "SELECT id, base_currency_id, quote_currency_id, price, trade_date FROM trade_log"
        )
        trade_logs = sqlite_cursor.fetchall()

        for log in trade_logs:
            trade_log_id, base_currency_id, quote_currency_id, price, trade_date = log
            trade_date_dt = datetime.fromtimestamp(trade_date)
            mysql_cursor.execute(
                """
                INSERT INTO trade_log (trade_log_id, base_currency_id, quote_currency_id, price, date_traded) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (trade_log_id, base_currency_id, quote_currency_id, price, trade_date_dt)
            )

        # Migrate transactions to transaction and create roles
        sqlite_cursor.execute(
            "SELECT uuid, balance_sender_id, balance_receiver_id, amount, transaction_date FROM transactions"
        )
        transactions = sqlite_cursor.fetchall()

        for transaction in transactions:
            uuid, sender_account_id, receiver_account_id, amount, transaction_date = transaction
            transaction_date_dt = datetime.fromtimestamp(transaction_date)
            mysql_cursor.execute(
                """
                INSERT INTO transaction (uuid, sender_account_id, receiver_account_id, amount, transaction_date) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (uuid.hex(), sender_account_id, receiver_account_id, amount, transaction_date_dt)
            )

            # If sender and receiver are the same, create a role
            if sender_account_id == receiver_account_id:
                mysql_cursor.execute(
                    "SELECT discord_id, currency_id FROM account WHERE account_id = %s",
                    (sender_account_id,)
                )
                account_data = mysql_cursor.fetchone()
                if account_data:
                    discord_id, currency_id = account_data
                    mysql_cursor.execute(
                        "INSERT INTO role (discord_id, role_number, currency_id) VALUES (%s, %s, %s)",
                        (discord_id, 1, currency_id)
                    )

        # Commit changes
        mysql_conn.commit()
        print("Migration completed successfully.")

        if sqlite_conn:
            sqlite_conn.close()
        if mysql_conn:
            mysql_conn.close()

    except sqlite3.Error as sqlite_error:
        print(f"SQLite error: {sqlite_error}")
    except pymysql.MySQLError as mysql_error:
        print(f"MySQL error: {mysql_error}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    sqlite_file = "currency.db"
    mysql_config = {
        "host": "localhost",
        "user": "root",
        "password": "secret",
        "port": 3307,
        "database": "smite_db"
    }

    migrate_sqlite_to_mysql(sqlite_file, mysql_config)
