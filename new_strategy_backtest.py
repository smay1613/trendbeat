from indicators import calculate_indicators
from logger_output import log
from trade_logic import trade_logic, determine_trend

import pandas as pd
from binance.client import Client
from state import *
from config import *
# Настройки

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


if BacktestConfig.enabled:
    log("Started")
    default_user = UserData('1')
    default_user.strategies.register_default_strategies()

    historical_data = get_historical_data(BacktestConfig.symbol, BacktestConfig.interval, BacktestConfig.start_date, BacktestConfig.end_date)
    historical_data = calculate_indicators(historical_data)
    try:
        for index, row in historical_data.iterrows():
            latest_price = row['close']
            timestamp = index

            if len(historical_data) >= 200:
                determine_trend(row)
                for strategy in default_user.strategies.strategies.values():
                    trade_logic(row, timestamp, latest_price, strategy, default_user)

            # Print current P&L for open positions
            # current_PL = 0
            # if long_position_opened:
            #     current_PL = (latest_price - long_entry_price) * (position_size / long_entry_price)
            # elif short_position_opened:
            #     current_PL = (short_entry_price - latest_price) * (position_size / short_entry_price)
            #
            # total_capital = current_capital + allocated_capital + current_PL

            # log(
            #     f"\nCurrent Balance: {current_capital:.8f}/{allocated_capital:.8f} = {total_capital:.8f}, P&L: {current_PL:.8f}\n"
            #     f"BTC: {latest_price}, Short: {short_position_opened}|{short_entry_price}|{stop_loss_short:.2f}, Long: {long_position_opened}|{long_entry_price}|{stop_loss_long:.2f}\n"
            #     f"=============================================")
    except Exception as e:
        log(f"Error occurred: {e}")

    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.2f}'.format)

    # trade_df = pd.DataFrame(BacktestState.trade_log)
    # total_profit_loss = BacktestState.current_capital + PositionState.allocated_capital - BacktestConfig.INITIAL_CAPITAL

    # if BacktestConfig.enabled:
    #     log(trade_df)
    #     log("Итоговые результаты:")
    #     BacktestState.dump()
