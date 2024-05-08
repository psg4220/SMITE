import enum
import io
import random
import sqlite3

import aiosqlite
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime

import Currency


class TimeScale(enum.Enum):
    SECOND = 1
    SECOND_5 = 5
    SECOND_10 = 10
    SECOND_30 = 30
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    DAY_2 = 172800
    WEEK = 604800
    MONTH = 2.6298e+6


# Define the Timeframe Enum to represent different time intervals
class Timeframe(enum.Enum):
    MINUTE_1 = 1 / 60  # 1 minute
    MINUTES_5 = 5 / 60  # 5 minutes
    MINUTES_15 = 15 / 60  # 15 minutes
    HOUR_1 = 1  # 1 hour
    HOURS_4 = 4  # 4 hours
    DAY_1 = 24  # 1 day
    WEEK_1 = 24 * 7  # 1 week


# Define a function to insert test data into trade_log with progressing trade_dates
def insert_ordered_trades(db_path, start_date, num_records, interval):
    """
    Inserts fake prices and incrementally increasing trade_dates into the trade_log table for testing.

    Parameters:
    db_path (str): Path to the SQLite database.
    start_date (datetime.datetime): The initial date to start from.
    num_records (int): Number of records to insert.
    interval (datetime.timedelta): Time increment between records.
    """
    # Create a connection to the SQLite database
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Create a Faker instance to generate realistic random data

    # Set the initial trade_date
    current_date = start_date

    # Loop to insert the specified number of records
    for _ in range(num_records):
        # Generate a random price
        price = round(random.uniform(1.00, 1000.00), 2)  # Random price between 1 and 1000

        # Convert datetime to Unix timestamp
        trade_date = int(current_date.timestamp())

        # Insert into the trade_log table
        cursor.execute(
            "INSERT INTO trade_log (base_currency_id, quote_currency_id, price, trade_date) VALUES (?, ?, ?, ?)",
            (1, 2, price, trade_date)
        )

        # Move to the next trade_date by adding the interval
        current_date += interval

    # Commit the transaction
    connection.commit()


# Updated function to plot trade logs with a specified timeframe (as an enum)
async def plot_trade_logs(db_path, base_ticker, quote_ticker, scale: TimeScale, limit=None):
    """
    Plots trade logs from an SQLite database within a given timeframe.

    Parameters:
    db_path (str): Path to the SQLite database.
    base_ticker (str): Base currency ticker symbol.
    quote_ticker (str): Quote currency ticker symbol.
    """
    base_currency_id = await Currency.get_currency_id(base_ticker, Currency.InputType.TICKER.value)
    quote_currency_id = await Currency.get_currency_id(quote_ticker, Currency.InputType.TICKER.value)
    if base_currency_id is None or quote_currency_id is None:
        return None
    # SQL query to fetch data within the specified timeframe
    query = f"""
        SELECT price, trade_date
        FROM trade_log
        WHERE base_currency_id = ?
        AND quote_currency_id = ?
        ORDER BY trade_date DESC 
        {'' if limit is None else 'LIMIT ?'}
    """
    if limit is None:
        query_input = (base_currency_id, quote_currency_id)
    else:
        query_input = (base_currency_id, quote_currency_id, limit)
    # Execute the query and fetch the data asynchronously
    async with aiosqlite.connect(db_path) as connection:
        async with connection.execute(
                query,
                query_input
        ) as cursor:
            data = await cursor.fetchall()

        # # Convert trade_date (Unix time) to formatted datetime strings
        trade_dates, prices = [], []
        if len(data) == 0:
            return None
        for row in data:
            trade_date = datetime.datetime.fromtimestamp(row[1], tz=datetime.UTC)
            price = row[0]
            trade_dates.append(trade_date)
            prices.append(price)
            if len(trade_dates) >= 2:
                if trade_dates[len(trade_dates) - 2].timestamp() <= \
                        trade_dates[len(trade_dates) - 1].timestamp() + scale.value:
                    trade_dates.pop()
                    prices.pop()

        plt.figure(figsize=[20, 10])
        plt.title(f"{base_ticker}/{quote_ticker} Price")
        datenums = mdates.date2num(trade_dates)
        fig = plt.gcf()
        ax = plt.gca()
        xfmt = mdates.DateFormatter('%Y-%m-%d %H:%M:%S')
        ax.xaxis.set_major_formatter(xfmt)
        plt.plot(datenums, prices, color='red')
        plt.fill_between(datenums, prices, color='red', alpha=0.3)
        fig.autofmt_xdate()
        plt.annotate(
            f'{prices[0]}',
            (trade_dates[0], prices[0]),
            textcoords='offset points',  # Positioning of the text relative to the point
            xytext=(80, 8),  # Offset of the text in points
            arrowprops=dict(arrowstyle='->', lw=1.5),
            fontsize=14
        )
        # Show the plot
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        return buffer


# insert_ordered_trades(db_path, datetime.datetime(2024, 5, 3, 0, 0, 0), 1000, datetime.timedelta(seconds=3600))


# def main():
#     asyncio.run(plot_trade_logs('currency.db' ,'XCEN', 'JTN', TimeScale.HOUR, limit=100))

# if __name__ == "__main__":
#     main()
