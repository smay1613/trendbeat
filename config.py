import copy
import os

from database_helper import get_database_helper
from formatting import format_price


class StrategyConfig:
    def __init__(self, name=None):
        self.name = name
        self.high_volume_only = True
        self.position_size = 100.0
        self.long_buy_rsi_enter = 80
        self.long_buy_additional_enter = 90
        self.long_buy_rsi_exit = 79
        self.short_sell_rsi_enter = 30
        self.short_sell_additional_enter = 20
        self.short_sell_rsi_exit = 31
        self.min_adx = 15
        self.allow_weak_trend = True
        self.close_on_trend_reverse = False
        self.leverage = 10

    def setup_risk_checks(self, min_adx=None, allow_weak_trend=None, close_on_trend_reverse=None, high_volume_only=None):
        if min_adx is not None:
            self.min_adx = min_adx

        if allow_weak_trend is not None:
            self.allow_weak_trend = allow_weak_trend

        if close_on_trend_reverse is not None:
            self.close_on_trend_reverse = close_on_trend_reverse

        if high_volume_only is not None:
            self.high_volume_only = high_volume_only

    def setup_long_position(self, enter=None, additional_enter=None, exit=None):
        if enter is not None:
            self.long_buy_rsi_enter = enter
        if additional_enter is not None:
            self.long_buy_additional_enter = additional_enter
        if exit is not None:
            self.long_buy_rsi_exit = exit

    def setup_short_position(self, enter=None, additional_enter=None, exit=None):
        if enter is not None:
            self.short_sell_rsi_enter = enter
        if additional_enter is not None:
            self.short_sell_additional_enter = additional_enter
        if exit is not None:
            self.short_sell_rsi_exit = exit

    def setup_position_settings(self, position_size=None, leverage=None):
        if position_size is not None:
            self.position_size = position_size
        if leverage:
            self.leverage = leverage

    def dump(self, risks=True, long_rsi=True, short_rsi=True, pos_size=True):
        strategy_config = (
            (f"📦 *Size*: `{format_price(self.position_size)} x{self.leverage}`\n" if pos_size else '') +
            (("🛡️ *Risk Management*\n"
            f"     🌀 `Strong Momentum`\n" +
            (f"     💹️ `Strong Trend`\n" if not self.allow_weak_trend else '') +
            (f"     🔄 `Reversal Stop`\n" if self.close_on_trend_reverse else '') +
            (f"     📊 `High Vol.` \n" if self.high_volume_only else '')) if risks else '') +
            # f"\n"
            (f"🍏 *Long RSI*\n"
             f"     📈 📍 `{self.long_buy_rsi_enter}` → `{self.long_buy_additional_enter}` 🔄 → `{self.long_buy_rsi_exit}` 🎯\n" if long_rsi else '') +
            # "\n"
            (f"🍎 *Short RSI*\n"
             f"     📉 📍 `{self.short_sell_rsi_enter}` → `{self.short_sell_additional_enter}` 🔄 → `{self.short_sell_rsi_exit}` 🎯\n" if short_rsi else '')
        )

        return strategy_config

    def load(self, row):
        for key, value in row.items():
            setattr(self, key, value)

    def store(self, strategy_id):
        data = copy.deepcopy(self.__dict__)
        data['strategy_id'] = strategy_id
        get_database_helper().store("strategy_config", data)
    # assert long_buy_rsi_enter < long_buy_rsi_exit
    # assert short_sell_rsi_exit < short_sell_rsi_enter

# class NeutralStrategyConfig:
#     high_volume_only = False
#     position_size = 4500.0
#     long_buy_rsi_enter = 56
#     long_buy_rsi_exit = 72
#     short_sell_rsi_enter = 62
#     short_sell_rsi_exit = 28
#     min_adx = 15


# class defaultparams:
#     long_buy_rsi_enter = 56
#     long_buy_rsi_exit = 82
#     short_sell_rsi_enter = 58
#     short_sell_rsi_exit = 28
#     min_adx = 15
#
# class ExtremeStrategyConfig:
#     high_volume_only = True
#     position_size = 4500.0
#     long_buy_rsi_enter = 32
#     long_buy_additional_enter = 23
#     long_buy_rsi_exit = 68
#     short_sell_rsi_enter = 82
#     short_sell_additional_enter = 90
#     short_sell_rsi_exit = 55
#     min_adx = 15
#     use_trend = False

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
    start_date = '1 Dec 2024'
    end_date = '12 Dec 2024' # TODO: CURRENT DATE!!!!!!!!!!!!

class RealTimeConfig:
    notify = True
    first_minute_check = True


class ConnectionsConfig:
    TESTNET_API_KEY = os.getenv("TESTNET_BINANCE_API_KEY")
    TESTNET_API_SECRET = os.getenv("TESTNET_BINANCE_API_SECRET")
    testnet_orders = True

    API_KEY = os.getenv("BINANCE_API_KEY")
    API_SECRET = os.getenv("BINANCE_API_SECRET")

    CHAT_ID = '313472352'  # Чат ID, куда будут отправляться сообщения (можно использовать ID пользователя)

class LogConfig:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

class CoinmarketCapConfig:
    API_KEY = os.getenv("COINMARKETCAP_KEY")

class ChartImgConfig:
    API_KEY = os.getenv('CHART_IMG_KEY')
    layout_id = os.getenv('CHART_IMG_CHART_ID')
    session_id = os.getenv('TRADINGVIEW_SESSION_ID')
    session_sign = os.getenv('TRADINGVIEW_SESSION_KEY')
    enabled = True