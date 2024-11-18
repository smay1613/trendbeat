import os


class StrategyConfig:
    high_volume_only = False
    position_size = 4500.0
    long_buy_rsi_enter = 56
    long_buy_rsi_exit = 72
    short_sell_rsi_enter = 62
    short_sell_rsi_exit = 28
    min_adx = 15

    assert long_buy_rsi_enter < long_buy_rsi_exit
    assert short_sell_rsi_exit < short_sell_rsi_enter

class defaultparams:
    long_buy_rsi_enter = 56
    long_buy_rsi_exit = 82
    short_sell_rsi_enter = 58
    short_sell_rsi_exit = 28
    min_adx = 15

class BacktestConfig:
    testnet_md = False
    enabled = False
    send_orders = True
    LEVERAGE = 15
    INITIAL_CAPITAL = 1000.0
    symbol = 'BTCUSDT'
    interval = '1h'
    lookback_period = '7 days ago UTC'
    start_date = '1 Jun 2024'
    end_date = '13 Sep 2024'

class RealTimeConfig:
    notify = True

class UserConfig:
    TESTNET_API_KEY = os.getenv("TESTNET_BINANCE_API_KEY")
    TESTNET_API_SECRET = os.getenv("TESTNET_BINANCE_API_SECRET")
    testnet_orders = True

    API_KEY = os.getenv("BINANCE_API_KEY")
    API_SECRET = os.getenv("BINANCE_API_SECRET")

    CHAT_ID = '313472352'  # Чат ID, куда будут отправляться сообщения (можно использовать ID пользователя)


class LogConfig:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
