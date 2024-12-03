import threading
import time

import pandas as pd

from config import BacktestConfig, StrategyConfig
from indicators import calculate_indicators
from logger_output import log
from new_strategy_backtest import client, get_historical_data
from fake_server import run_web_server
from trade_logic import trade_logic, determine_trend


def rsi_conditions(rsi):
    if rsi > 90:
        return "strong overbuy"
    elif rsi > 70:
        return "overbuy"
    elif rsi < 30:
        return "oversell"
    elif rsi < 20:
        return "strong oversell"

    return "neutral"


def rsi_condition_icon(rsi):
    condition = rsi_conditions(rsi)
    return "🔴" if "oversell" in condition else \
        "🟡" if "overbuy" in condition else \
            '🟢'


def decision_icon(is_good):
    return '✅' if is_good else '⚠️'


def trend_icon(trend, type):
    return "🔼" if trend == "LONG" and type == "WEAK" else "⏫" if trend == "LONG" else \
        "🔽" if type == "WEAK" else "⏬"


def get_price(symbol):
    # Получение текущей рыночной цены
    ticker = client.futures_symbol_ticker(symbol=symbol)
    return float(ticker['price'])


threading.Thread(target=run_web_server, daemon=True).start()

# Загрузить начальные исторические данные
historical_data = get_historical_data(BacktestConfig.symbol, BacktestConfig.interval, BacktestConfig.lookback_period,
                                      "now")
historical_data = calculate_indicators(historical_data)
log(f"History loaded ({BacktestConfig.lookback_period})")
# Бесконечный цикл для подгрузки новых данных и выполнения расчета
while True:
    try:
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

        # Проверка, добавлена ли новая свеча
        if new_data.index[-1] > historical_data.index[-1]:
            # Добавить новую свечу к историческим данным
            historical_data = pd.concat([historical_data, new_data])
            historical_data = calculate_indicators(historical_data)  # Пересчитать индикаторы

            # Выполнить торговые решения
            row = historical_data.iloc[-1]

            trend, trend_type = determine_trend(row)
            formatted_data = {key: value for key, value in list(row.to_dict().items())}

            def format_price(price):
                return f'{int(price):,}$'

            trend_icon_separator = '🔺' if trend == 'LONG' else '🔻'
            log(
                f"*{BacktestConfig.symbol} Market Overview*\n"
                f"\n📌 *Market Trend*\n"
                f"\* `{trend}|{trend_type}` {trend_icon(trend, trend_type)}\n"
                f"\n📈 *Trend Strength (ADX)*\n"
                f"\* Current:    `{formatted_data['ADX']:.0f}` {decision_icon(formatted_data['ADX'] > StrategyConfig.min_adx)}\n"
                f"\* Threshold:  `{StrategyConfig.min_adx}`\n"
                f"\n💰 *Price*\n"
                f"\* Current:  `{format_price(formatted_data['close'])}`\n"
                f"\* Range:    `{format_price(formatted_data['low'])} - {format_price(formatted_data['high'])}`\n"
                f"\n📊 *Volume*\n"
                f"\* Current:  `{formatted_data['volume']:.0f}` {decision_icon(formatted_data['volume'] > formatted_data['Average_Volume'])}\n"
                f"\* Average:  `{formatted_data['Average_Volume']:.0f}`\n"
                f"\n📊 *EMA Indicators* \n"
                f"{trend_icon_separator} EMA 7 (_Current_):  `{format_price(formatted_data['EMA_7'])}`\n"
                f"{trend_icon_separator} EMS 25 (_Short_):   `{format_price(formatted_data['EMA_25'])}`\n"
                f"{trend_icon_separator} EMA 50 (_Mid_):     `{format_price(formatted_data['EMA_99'])}`\n"
                f"\n{rsi_condition_icon(formatted_data['RSI_6'])} *RSI* (_6{BacktestConfig.interval_period}_)\n"
                f"\* Current: `{formatted_data['RSI_6']:.1f}` (_{rsi_conditions(formatted_data['RSI_6'])}_) {decision_icon(rsi_conditions(formatted_data['RSI_6']) == 'neutral')}\n"
                f"\n📉 *Support Levels*\n"
                f"🔹 Immediate (_7{BacktestConfig.interval_period}_):    `{format_price(formatted_data['Support_7'])}`\n"
                f"🔹 Short term (_25{BacktestConfig.interval_period}_):  `{format_price(formatted_data['Support_25'])}`\n"
                f"🔹 Mid term (_50{BacktestConfig.interval_period}_):    `{format_price(formatted_data['Support_50'])}`\n"
                f"\n📈 *Resistance Levels*\n"
                f"🔸 Immediate (_7{BacktestConfig.interval_period}_):    `{format_price(formatted_data['Resistance_7'])}`\n"
                f"🔸 Short term (_25{BacktestConfig.interval_period}_):  `{format_price(formatted_data['Resistance_25'])}`\n"
                f"🔸 Mid term (_50{BacktestConfig.interval_period}_):    `{format_price(formatted_data['Resistance_50'])}`\n"
            )

            latest_price = row['close']
            trade_logic(row, timestamp=new_data.index[-1], latest_price=latest_price)

        # Пауза перед повторной проверкой (можно настроить интервал проверки)
        time.sleep(60)  # Например, 1 минута

    except Exception as e:
        log(f"Error occurred: {e}")
        time.sleep(300)  # Ожидание перед повторной попыткой
