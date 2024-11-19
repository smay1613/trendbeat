import threading
import time

import pandas as pd

from config import BacktestConfig, StrategyConfig
from indicators import calculate_indicators
from logger_output import log
from new_strategy_backtest import client, get_historical_data
from fake_server import run_web_server
from trade_logic import trade_logic, determine_trend, rsi_conditions

threading.Thread(target=run_web_server, daemon=True).start()

# Загрузить начальные исторические данные
historical_data = get_historical_data(BacktestConfig.symbol, BacktestConfig.interval, BacktestConfig.lookback_period, "now")
historical_data = calculate_indicators(historical_data)
log(f"History loaded ({BacktestConfig.lookback_period})")
# Бесконечный цикл для подгрузки новых данных и выполнения расчета
while True:
    try:
        # Получить последнюю свечу с сервера
        new_kline = client.futures_klines(symbol=BacktestConfig.symbol, interval=BacktestConfig.interval, limit=1)
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

        # Проверка, добавлена ли новая свеча
        if new_data.index[-1] > historical_data.index[-1]:

            # Добавить новую свечу к историческим данным
            historical_data = pd.concat([historical_data, new_data])
            historical_data = calculate_indicators(historical_data)  # Пересчитать индикаторы

            # Выполнить торговые решения
            row = historical_data.iloc[-1]

            trend, trend_type = determine_trend(row)
            formatted_data = {key: value for key, value in list(row.to_dict().items())}
            log(f"{BacktestConfig.symbol} | {int(formatted_data['close'])}$ ({int(formatted_data['low'])}$-{int(formatted_data['high'])}$)"
                f"\nVol: {formatted_data['volume']:.2f} (avg: {formatted_data['Average_Volume']:.2f})"
                f"\nADX: {formatted_data['ADX']:.2f} (min: {StrategyConfig.min_adx})"
                f"\nEMA 7: {formatted_data['EMA_7']:.0f} | EMA 25: {formatted_data['EMA_25']:.0f} | EMA 50: {formatted_data['EMA_99']:.0f}"
                f"\nRSI 6: {formatted_data['RSI_6']:.1f} ({rsi_conditions(formatted_data['RSI_6'])}) | RSI 15: {formatted_data['RSI_15']:.2f}"
                f"\nMarket trend: {trend}|{trend_type}")

            latest_price = row['close']
            trade_logic(row, timestamp=new_data.index[-1], latest_price=latest_price)

        # Пауза перед повторной проверкой (можно настроить интервал проверки)
        time.sleep(60)  # Например, 1 минута

    except Exception as e:
        log(f"Error occurred: {e}")
        time.sleep(300)  # Ожидание перед повторной попыткой