import datetime
import threading
import time
import traceback

import pandas as pd
from binance import Client

import market_overview
from config import BacktestConfig, RealTimeConfig, ConnectionsConfig
from fake_server import run_web_server
from indicators import calculate_indicators
from logger_output import log, log_error
from state import UserManager
from tg_input import run_bot_server
from trade_logic import trade_logic

client = Client(ConnectionsConfig.TESTNET_API_KEY if BacktestConfig.testnet_md else ConnectionsConfig.API_KEY,
                ConnectionsConfig.TESTNET_API_SECRET if BacktestConfig.testnet_md else ConnectionsConfig.API_SECRET,
                testnet=BacktestConfig.testnet_md)

class HistoricalDataLoader:
    def __init__(self):
        self.historical_data = self.get_historical_data(BacktestConfig.symbol, BacktestConfig.interval,
                                                        BacktestConfig.lookback_period,
                                                        "now")
        self.historical_data = calculate_indicators(self.historical_data)
        log(f"History loaded / {BacktestConfig.interval} ({BacktestConfig.lookback_period})")

    def format_data(self, df):
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['open'] = df['open'].astype(float)
        df['volume'] = df['volume'].astype(float)

        return df

    def get_historical_data(self, symbol, interval, start_date, end_date):
        klines = client.futures_historical_klines(symbol, interval, start_date, end_date)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'])

        df = self.format_data(df)

        return df[['close', 'high', 'low', 'open', 'volume']]

    def get_last(self):
        # Получить последнюю свечу с сервера
        new_kline = client.futures_klines(symbol=BacktestConfig.symbol, interval=BacktestConfig.interval, limit=2)
        new_kline = [new_kline[0]]
        new_data = pd.DataFrame(new_kline, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])

        new_data = self.format_data(new_data)

        return new_data

    def get_update(self):
        try:
            new_data = self.get_last()
        except Exception as e:
            log_error(f"Error while getting last candle: {e}\n"
                      f"{traceback.format_exc()}")
            return None

        if new_data.index[-1] > self.historical_data.index[-1]:
            previous_row = self.historical_data.iloc[-1]
            self.historical_data = pd.concat([self.historical_data, new_data])
            self.historical_data = calculate_indicators(self.historical_data)
            row = self.historical_data.iloc[-1]
            timestamp = new_data.index[-1]
            return row, previous_row, timestamp

        return None


threading.Thread(target=run_web_server, daemon=True).start()

try:
    user_manager = UserManager()
    history_data_loader = HistoricalDataLoader()
except Exception as e:
    log_error(f"Startup failed! {e}\n"
              f"{traceback.format_exc()}")

def main_loop():
    while True:
        try:
            def is_first_minute():
                current_minute = datetime.datetime.now().minute
                return current_minute == 1

            if RealTimeConfig.first_minute_check and not is_first_minute():
                time.sleep(60)
                continue

            update = history_data_loader.get_update()
            if update:
                row, previous_row, timestamp = update
                try:
                    market_overview.overview_printer.append_market_overview(row, previous_row)
                except Exception as e:
                    log_error(f"Failed to append market overview! {e}\n"
                              f"{traceback.format_exc()}")
                latest_price = row['close']

                for user_data in list(user_manager.users.values()):
                    for strategy in user_data.strategies.strategies.values():
                        trade_logic(row, strategy=strategy, timestamp=timestamp, latest_price=latest_price, user=user_data)

            if not RealTimeConfig.first_minute_check:
                time.sleep(60)

        except Exception as e:
            log_error(f"Error occurred: {e}\n"
                f"{traceback.format_exc()}")
            time.sleep(300)  # Ожидание перед повторной попыткой


threading.Thread(target=main_loop, daemon=True).start()
try:
    run_bot_server(user_manager)
except Exception as e:
    log_error(f"Running bot failed! {e}\n"
              f"{traceback.format_exc()}")
