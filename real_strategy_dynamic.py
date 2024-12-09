import datetime
import threading
import time

import pandas as pd
from binance import Client

from config import BacktestConfig, RealTimeConfig, ConnectionsConfig
from fake_server import run_web_server
from indicators import calculate_indicators
from logger_output import log
from database_helper import DatabaseHelper
from market_overview import broadcast_market_overview
from tg_input import UserManager, run_bot_server
from trade_logic import trade_logic

client = Client(ConnectionsConfig.TESTNET_API_KEY if BacktestConfig.testnet_md else ConnectionsConfig.API_KEY,
                ConnectionsConfig.TESTNET_API_SECRET if BacktestConfig.testnet_md else ConnectionsConfig.API_SECRET,
                testnet=BacktestConfig.testnet_md)

def get_historical_data(symbol, interval, start_date, end_date):
    klines = client.futures_historical_klines(symbol, interval, start_date, end_date)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
        'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
        'taker_buy_quote_asset_volume', 'ignore'])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['open'] = df['open'].astype(float)

    return df[['close', 'high', 'low', 'open', 'volume']]

threading.Thread(target=run_web_server, daemon=True).start()

# Загрузить начальные исторические данные
historical_data = get_historical_data(BacktestConfig.symbol, BacktestConfig.interval, BacktestConfig.lookback_period,
                                      "now")
historical_data = calculate_indicators(historical_data)
log(f"History loaded ({BacktestConfig.lookback_period})")

# DatabaseHelper.initialize("bot_database.sqlite")

DatabaseHelper.initialize(ConnectionsConfig.SUPABASE_URL, ConnectionsConfig.SUPABASE_KEY)

user_manager = UserManager()
# threading.Thread(target=run_bot_server, args=(user_manager,), daemon=True).start()

# Бесконечный цикл для подгрузки новых данных и выполнения расчета
def main_loop():
    while True:
        try:
            def is_first_minute():
                current_minute = datetime.datetime.now().minute
                return current_minute == 1

            if RealTimeConfig.first_minute_check and not is_first_minute():
                time.sleep(60)
                continue

            # Получить последнюю свечу с сервера
            new_kline = client.futures_klines(symbol=BacktestConfig.symbol, interval=BacktestConfig.interval, limit=2)
            new_kline = [new_kline[0]]
            new_data = pd.DataFrame(new_kline, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume', 'ignore'
            ])

            new_data['timestamp'] = pd.to_datetime(new_data['timestamp'], unit='ms')
            new_data.set_index('timestamp', inplace=True)
            new_data['close'] = new_data['close'].astype(float)
            new_data['high'] = new_data['high'].astype(float)
            new_data['low'] = new_data['low'].astype(float)
            new_data['open'] = new_data['open'].astype(float)
            new_data['volume'] = new_data['volume'].astype(float)
            global historical_data
            if new_data.index[-1] > historical_data.index[-1]:
                previous_row = historical_data.iloc[-1]

                # Добавить новую свечу к историческим данным
                historical_data = pd.concat([historical_data, new_data])
                historical_data = calculate_indicators(historical_data)  # Пересчитать индикаторы

                # Выполнить торговые решения
                row = historical_data.iloc[-1]

                broadcast_market_overview(row, previous_row, user_manager.users)

                latest_price = row['close']

                for user_id, user_data in list(user_manager.users.items()):
                    trade_logic(row, timestamp=new_data.index[-1], latest_price=latest_price, user=user_data, user_id=user_id)

            if not RealTimeConfig.first_minute_check:
                time.sleep(60)

        except Exception as e:
            log(f"Error occurred: {e}")
            time.sleep(300)  # Ожидание перед повторной попыткой


threading.Thread(target=main_loop, daemon=True).start()
run_bot_server(user_manager)