import os


class StrategyConfig:
    high_volume_only = True
    position_size = 4500.0
    long_buy_rsi_enter = 32
    long_buy_additional_enter = 23
    long_buy_rsi_exit = 68
    short_sell_rsi_enter = 82
    short_sell_additional_enter = 90
    short_sell_rsi_exit = 55
    min_adx = 15
    use_trend = False

    assert long_buy_rsi_enter < long_buy_rsi_exit
    assert short_sell_rsi_exit < short_sell_rsi_enter

    # def dump(self):
    #     log("*Strategy configuration*\n"
    #         f"\* High volume only: {self.high_volume_only}"
    #         f"\* [Long/Buy] Enter RSI: {self.long_buy_rsi_enter}"
    #         f"\* [Long/Buy] Addtional enter RSI: {self.long_buy_additional_enter}"
    #         f"\* [Long/Buy] Exit RSI: {self.long_buy_rsi_exit}"
    #         )
# class NeutralStrategyConfig:
#     high_volume_only = False
#     position_size = 4500.0
#     long_buy_rsi_enter = 56
#     long_buy_rsi_exit = 72
#     short_sell_rsi_enter = 62
#     short_sell_rsi_exit = 28
#     min_adx = 15


class defaultparams:
    long_buy_rsi_enter = 56
    long_buy_rsi_exit = 82
    short_sell_rsi_enter = 58
    short_sell_rsi_exit = 28
    min_adx = 15

class ExtremeStrategyConfig:
    high_volume_only = True
    position_size = 4500.0
    long_buy_rsi_enter = 32
    long_buy_additional_enter = 23
    long_buy_rsi_exit = 68
    short_sell_rsi_enter = 82
    short_sell_additional_enter = 90
    short_sell_rsi_exit = 55
    min_adx = 15
    use_trend = False

class BacktestConfig:
    testnet_md = False
    enabled = False
    send_orders = True
    LEVERAGE = 15
    INITIAL_CAPITAL = 1000.0
    symbol = 'BTCUSDT'
    interval_period = 'h'
    interval = f'1{interval_period}'
    lookback_period = '7 days ago UTC'
    start_date = '11 Dec 2024'
    end_date = '12 Dec 2024' # TODO: CURRENT DATE!!!!!!!!!!!!

class RealTimeConfig:
    notify = True
    first_minute_check = False


class ConnectionsConfig:
    TESTNET_API_KEY = os.getenv("TESTNET_BINANCE_API_KEY")
    TESTNET_API_SECRET = os.getenv("TESTNET_BINANCE_API_SECRET")
    testnet_orders = True

    API_KEY = os.getenv("BINANCE_API_KEY")
    API_SECRET = os.getenv("BINANCE_API_SECRET")

    CHAT_ID = '313472352'  # Чат ID, куда будут отправляться сообщения (можно использовать ID пользователя)

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class LogConfig:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

class CoinmarketCapConfig:
    API_KEY = os.getenv("COINMARKETCAP_KEY")