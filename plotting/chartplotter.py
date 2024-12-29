import mplfinance as mpf
import pandas as pd
from datetime import timedelta
import io
from services.tradelogservice import TradeLogService


class ChartPlotter:
    def __init__(self, base_currency_id: int, quote_currency_id: int, time_period: timedelta = None, chart_type='line'):
        self.base_currency_id = base_currency_id
        self.quote_currency_id = quote_currency_id
        self.time_period = time_period
        self.chart_type = chart_type
        self.data_frame = None
        self.resample_rule = "min"
        self.image_bytes = io.BytesIO()

    def add_moving_average(self, window=14):
        """
        Add a moving average to the DataFrame.
        :param window: Number of periods for calculating the moving average.
        """
        self.data_frame[f"MA_{window}"] = self.data_frame['Close'].rolling(window=window).mean()

    def calculate_rsi(self, window=14):
        """
        Calculate the Relative Strength Index (RSI).
        :param window: Number of periods for calculating RSI.
        """
        delta = self.data_frame['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

        rs = gain / loss
        self.data_frame['RSI'] = 100 - (100 / (1 + rs))

    def calculate_macd(self, short_window=12, long_window=26, signal_window=9):
        """
        Calculate the MACD and Signal Line.
        :param short_window: The short EMA window.
        :param long_window: The long EMA window.
        :param signal_window: The signal line EMA window.
        """
        short_ema = self.data_frame['Close'].ewm(span=short_window, adjust=False).mean()
        long_ema = self.data_frame['Close'].ewm(span=long_window, adjust=False).mean()

        self.data_frame['MACD'] = short_ema - long_ema
        self.data_frame['Signal_Line'] = self.data_frame['MACD'].ewm(span=signal_window, adjust=False).mean()

    def calculate_bollinger_bands(self, window=20, num_std_dev=2):
        """
        Calculate Bollinger Bands.
        :param window: Number of periods for the moving average.
        :param num_std_dev: Number of standard deviations for the bands.
        """
        rolling_mean = self.data_frame['Close'].rolling(window=window).mean()
        rolling_std = self.data_frame['Close'].rolling(window=window).std()

        self.data_frame['Bollinger_Upper'] = rolling_mean + (rolling_std * num_std_dev)
        self.data_frame['Bollinger_Lower'] = rolling_mean - (rolling_std * num_std_dev)

    async def fetch_data(self):
        """
        Fetch trade logs and prepare a DataFrame for plotting.
        """
        trade_logs = await TradeLogService.get_trade_logs_by_currency_pair(
            self.base_currency_id, self.quote_currency_id, time_delta=self.time_period
        )

        if not trade_logs:
            raise FileNotFoundError("No trade logs found.")

        ohlc_data = {
            'Date': [],
            'Price': [],
            'Open': [],
            'High': [],
            'Low': [],
            'Close': [],
        }

        for log in trade_logs:
            ohlc_data['Date'].append(log.date_traded)
            ohlc_data['Price'].append(log.price)
            ohlc_data['Open'].append(log.price)
            ohlc_data['High'].append(log.price)
            ohlc_data['Low'].append(log.price)
            ohlc_data['Close'].append(log.price)

        # Convert to DataFrame and set index
        df = pd.DataFrame(ohlc_data)
        df.set_index('Date', inplace=True)
        self.data_frame = df.apply(pd.to_numeric, errors='coerce')

    def determine_resample_rule(self):
        """
        Adjust the resample rule dynamically based on the number of rows in the dataset.
        """
        num_rows = len(self.data_frame)
        if num_rows < 100:
            self.resample_rule = "min"
        elif num_rows < 500:
            self.resample_rule = "5min"
        elif num_rows < 2000:
            self.resample_rule = "15min"
        else:
            self.resample_rule = "1h"

    def resample_data(self):
        """
        Resample the data according to the dynamically determined rule.
        """
        self.determine_resample_rule()
        self.data_frame = self.data_frame.resample(self.resample_rule).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Price': 'mean'
        }).dropna()

    def plot_chart(self):
        """
        Plot the chart with optional indicators and save it to an in-memory byte buffer.
        """
        figsize = (15, 10)  # Adjust size for multiple panels
        additional_plots = []
        panel_count = 1  # Start with the main panel

        # Add Moving Average
        if f"MA_{14}" in self.data_frame.columns:
            additional_plots.append(mpf.make_addplot(self.data_frame[f"MA_{14}"], color='blue'))

        # Add RSI as a separate subplot
        if 'RSI' in self.data_frame.columns:
            rsi_plot = mpf.make_addplot(self.data_frame['RSI'], panel=panel_count, color='purple', ylabel='RSI')
            additional_plots.append(rsi_plot)
            panel_count += 1

        # Add MACD as a separate subplot
        if 'MACD' in self.data_frame.columns and 'Signal_Line' in self.data_frame.columns:
            macd_plot = mpf.make_addplot(self.data_frame['MACD'], panel=panel_count, color='green', ylabel='MACD')
            signal_plot = mpf.make_addplot(self.data_frame['Signal_Line'], panel=panel_count, color='red')
            additional_plots.extend([macd_plot, signal_plot])
            panel_count += 1

        # Add Bollinger Bands to the main panel
        if 'Bollinger_Upper' in self.data_frame.columns and 'Bollinger_Lower' in self.data_frame.columns:
            additional_plots.append(mpf.make_addplot(self.data_frame['Bollinger_Upper'], color='orange'))
            additional_plots.append(mpf.make_addplot(self.data_frame['Bollinger_Lower'], color='orange'))

        # Dynamically create panel ratios
        panel_ratios = [4] + [2] * (panel_count - 1)

        mpf.plot(
            self.data_frame,
            type='candle' if self.chart_type == 'candlestick' else 'line',
            style='charles',
            xlabel="Time",
            ylabel="Price",
            savefig=dict(fname=self.image_bytes, format='png'),
            figsize=figsize,
            addplot=additional_plots,
            panel_ratios=panel_ratios  # Dynamically adjust panel ratios
        )
        self.image_bytes.seek(0)

    async def generate_chart(self, indicators=None):
        """
        Main method to fetch, process, and plot the chart with optional indicators.
        :param indicators: List of indicators to apply (e.g., ['RSI', 'MA', 'MACD', 'Bollinger']).
        """
        await self.fetch_data()
        self.resample_data()

        if indicators:
            for indicator in indicators:
                if indicator == 'MA':
                    self.add_moving_average(window=14)
                elif indicator == 'RSI':
                    self.calculate_rsi(window=14)
                elif indicator == 'MACD':
                    self.calculate_macd()
                elif indicator == 'Bollinger':
                    self.calculate_bollinger_bands()

        self.plot_chart()
        return self.image_bytes.getvalue()


# # Example usage
# async def main():
#     plotter = ChartPlotter(base_currency_id=7, quote_currency_id=8)
#     image = await plotter.generate_chart()
#
#     with open("chart_with_indicators.png", "wb") as f:
#         f.write(image)
#     print("Chart saved as 'chart_with_indicators.png'.")
#
#
# if __name__ == "__main__":
#     import asyncio
#
#     asyncio.run(main())
