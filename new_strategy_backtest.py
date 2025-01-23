import traceback

from indicators import calculate_indicators
from historical_data_loader import HistoricalDataLoader
from state import *
from trade_logic import trade_logic, determine_trend

# Настройки
#
# client = Client(ConnectionsConfig.TESTNET_API_KEY if BacktestConfig.testnet_md else ConnectionsConfig.API_KEY,
#                 ConnectionsConfig.TESTNET_API_SECRET if BacktestConfig.testnet_md else ConnectionsConfig.API_SECRET,
#                 testnet=BacktestConfig.testnet_md)

# def get_historical_data(symbol, interval, start_date, end_date):
#     klines = client.futures_historical_klines(symbol, interval, start_date, end_date)
#     df = pd.DataFrame(klines, columns=[
#         'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
#         'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
#         'taker_buy_quote_asset_volume', 'ignore'])
#
#     df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
#     df.set_index('timestamp', inplace=True)
#     df['close'] = df['close'].astype(float)
#     df['high'] = df['high'].astype(float)
#     df['low'] = df['low'].astype(float)
#     df['open'] = df['open'].astype(float)
#
#     return df[['close', 'high', 'low', 'open', 'volume']]


if BacktestConfig.enabled:
    log("Started")

    user_manager = UserManager()
    history_data_loader = HistoricalDataLoader(backload=False)

    default_user = UserData('1')
    default_user.strategies.register_default_strategies()

    # historical_data = history_data_loader.get_historical_data(BacktestConfig.symbol, BacktestConfig.interval, BacktestConfig.start_date, BacktestConfig.end_date)
    # historical_data = calculate_indicators(historical_data)
    try:
        for index, row in history_data_loader.historical_data.iterrows():
            latest_price = row['close']
            timestamp = index

            determine_trend(row)
            for strategy in default_user.strategies.strategies.values():
                trade_logic(row, timestamp, latest_price, strategy, default_user)

        for strategy in default_user.strategies.strategies.values():
            print(f"{strategy.strategy_config.name}\n"
                f"{strategy.stats.dump()}\n"
                f"PNL: {strategy.stats.cumulative_profit_loss}")

    except Exception as e:
        print(f"Error occurred: {e}\n"
            f"{traceback.format_exc()}")