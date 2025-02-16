import threading
import traceback

import pandas as pd
from binance import Client, ThreadedWebsocketManager

from config import ConnectionsConfig, BacktestConfig
from indicators import calculate_indicators
from logger_output import log, log_error

client = Client(ConnectionsConfig.TESTNET_API_KEY if BacktestConfig.testnet_md else ConnectionsConfig.API_KEY,
                ConnectionsConfig.TESTNET_API_SECRET if BacktestConfig.testnet_md else ConnectionsConfig.API_SECRET,
                testnet=BacktestConfig.testnet_md)


class HistoricalDataLoader:
    def __init__(self, handler_callback=None, backload=True, forward_load=True):
        self.historical_data = self.get_historical_data(BacktestConfig.symbol, BacktestConfig.interval,
                                                        BacktestConfig.lookback_period if backload else BacktestConfig.start_date,
                                                        "now")
        self.historical_data = calculate_indicators(self.historical_data)
        log(f"History loaded / {BacktestConfig.interval} ({BacktestConfig.lookback_period})")

        if forward_load:
            self.twm = None
            self.handler_callback = handler_callback
            self.ws_thread = threading.Thread(target=self.run_websocket, daemon=True)
            self.ws_thread.start()

            log("Kline socket is started")

    def run_websocket(self):
        self.twm = ThreadedWebsocketManager()
        self.twm.start()
        self.twm.start_kline_futures_socket(callback=self.handle_kline, symbol=BacktestConfig.symbol,
                                            interval=BacktestConfig.interval)

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

    # def get_last(self):
    #     # Получить последнюю свечу с сервера
    #     new_kline = client.futures_klines(symbol=BacktestConfig.symbol, interval=BacktestConfig.interval, limit=2)
    #     new_kline = [new_kline[0]]
    #     new_data = pd.DataFrame(new_kline, columns=[
    #         'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
    #         'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
    #         'taker_buy_quote_asset_volume', 'ignore'
    #     ])
    #
    #     new_data = self.format_data(new_data)
    #
    #     return new_data

    # def get_update(self):
    #     try:
    #         new_data = self.get_last()
    #         return self.append_candle(new_data)
    #     except Exception as e:
    #         log_error(f"Error while getting last candle: {e}\n"
    #                   f"{traceback.format_exc()}")
    #         return None

    def append_candle(self, new_data):
        if new_data.index[-1] > self.historical_data.index[-1]:
            previous_row = self.historical_data.iloc[-1]
            self.historical_data = pd.concat([self.historical_data, new_data])
            self.historical_data = calculate_indicators(self.historical_data)
            row = self.historical_data.iloc[-1]
            timestamp = new_data.index[-1]
            return row, previous_row, timestamp

        return None

    def handle_kline(self, msg):
        try:
            kline = msg['k']
            if not kline['x']:
                return

            new_data = pd.DataFrame([{
                'timestamp': kline['t'],
                'open': float(kline['o']),
                'high': float(kline['h']),
                'low': float(kline['l']),
                'close': float(kline['c']),
                'volume': float(kline['v']),
            }])

            new_data = self.format_data(new_data)
            append_result = self.append_candle(new_data)
            if not append_result:
                log_error("Empty kline append result!")
            else:
                self.handler_callback(append_result)
        except Exception as candle_exception:
            log_error(f"Failed to process socket k-line: {candle_exception}\n"
                      f"{traceback.format_exc()}")