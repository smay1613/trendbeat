from log_trade import log_trade
from config import StrategyConfig
from state import *


# TODO: FIX
def is_high_volume(row):
    return float(row['volume']) > row['Average_Volume']

def calculate_position_size(price, atr):
    """Расчет размера позиции на основе капитала и риска."""
    # risk_per_trade = MAX_RISK_PER_TRADE * current_capital
    position_size = 300.0 #risk_per_trade / atr  # учитываем волатильность
    return position_size * BacktestConfig.LEVERAGE

def determine_trend(row):
    ema_7 = row['EMA_7']
    ema_25 = row['EMA_25']
    ema_99 = row['EMA_99']
    old_trend_type = MarketState.trend_type
    old_trend = MarketState.trend
    if ema_7 < ema_25:
        MarketState.trend = "SHORT"
        MarketState.trend_type = "STRONG" if ema_7 < ema_99 else "WEAK"
    else:
        MarketState.trend = "LONG"
        MarketState.trend_type = "WEAK" if ema_7 < ema_99 else "STRONG"

    if MarketState.trend_type != old_trend_type or MarketState.trend != old_trend:
        log(f"[Alert] Trend changes to {MarketState.trend}|{MarketState.trend_type}")

    return MarketState.trend, MarketState.trend_type


def trade_logic(row, timestamp, latest_price):

    rsi_6 = row['RSI_6']
    # atr = row['ATR']
    adx = row['ADX']
    # macd = row['MACD']
    # Calculate max drawdown
    BacktestState.max_balance = max(BacktestState.max_balance, BacktestState.current_capital)
    drawdown = (BacktestState.max_balance - BacktestState.current_capital) / BacktestState.max_balance * 100
    BacktestState.max_drawdown = max(BacktestState.max_drawdown, drawdown)

    # Trade Logic
    if adx > StrategyConfig.min_adx and (not StrategyConfig.high_volume_only or is_high_volume(row)):
        position_size = StrategyConfig.position_size

        if MarketState.trend_type != "STRONG":
            # log(f"{timestamp} Trend is not strong, no decision")
            return

        if MarketState.trend == "LONG":
            if PositionState.short_position_opened:
                PositionState.short_position_opened = False
                log_trade(timestamp, 'Close Short', latest_price, position_size, "Trend reversal")

            if PositionState.long_position_opened and rsi_6 > StrategyConfig.long_buy_rsi_exit:
                PositionState.long_position_opened = False
                log_trade(timestamp, 'Close Long', latest_price, position_size, f"RSI > {StrategyConfig.long_buy_rsi_exit}")

            if not PositionState.long_position_opened and rsi_6 < StrategyConfig.long_buy_rsi_enter:
                PositionState.long_position_opened = True
                log_trade(timestamp, 'Open Long', latest_price, position_size, f"RSI < {StrategyConfig.long_buy_rsi_enter}")

        elif MarketState.trend == "SHORT":
            if PositionState.long_position_opened:
                PositionState.long_position_opened = False
                log_trade(timestamp, 'Close Long', latest_price, position_size, "Trend reversal")

            if PositionState.short_position_opened and rsi_6 < StrategyConfig.short_sell_rsi_exit:
                PositionState.short_position_opened = False
                log_trade(timestamp, 'Close Short', latest_price, position_size, f"RSI < {StrategyConfig.short_sell_rsi_exit}")

            if not PositionState.short_position_opened and rsi_6 > StrategyConfig.short_sell_rsi_enter:
                PositionState.short_position_opened = True
                log_trade(timestamp, 'Open Short', latest_price, position_size, f"RSI > {StrategyConfig.short_sell_rsi_enter}")
