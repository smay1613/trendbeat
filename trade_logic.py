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

# TODO: BROADCAST CHANGE
def determine_trend(row, user=None, user_id=None):
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
        if not user_id or user.user_settings.alerts_enabled:
            log(f"\[Alert] Trend changes to {MarketState.trend}|{MarketState.trend_type}",
                user=user_id)

    return MarketState.trend, MarketState.trend_type


def trade_logic(row, timestamp, latest_price, user, user_id):

    rsi_6 = row['RSI_6']
    # atr = row['ATR']
    adx = row['ADX']
    # macd = row['MACD']
    # Calculate max drawdown

    # Trade Logic
    if adx > StrategyConfig.min_adx and (not StrategyConfig.high_volume_only or is_high_volume(row)):
        position_size = StrategyConfig.position_size

        if StrategyConfig.use_trend and MarketState.trend_type != "STRONG":
            # log(f"{timestamp} Trend is not strong, no decision")
            return

        user_position_state = user.position_state

        if MarketState.trend == "LONG":
            if user_position_state.short_position_opened and StrategyConfig.use_trend:
                user_position_state.short_position_opened = False
                log_trade(timestamp, 'Close Short', latest_price, user_position_state.short_entry_size, "Trend reversal", user, user_id)

            if user_position_state.long_position_opened and rsi_6 > StrategyConfig.long_buy_rsi_exit:
                user_position_state.long_position_opened = False
                log_trade(timestamp, 'Close Long', latest_price, user_position_state.long_entry_size, f"RSI > {StrategyConfig.long_buy_rsi_exit}", user, user_id)

            if not user_position_state.long_position_opened and rsi_6 < StrategyConfig.long_buy_rsi_enter:
                user_position_state.long_position_opened = True
                log_trade(timestamp, 'Open Long', latest_price, position_size, f"RSI < {StrategyConfig.long_buy_rsi_enter}", user, user_id)

            if user_position_state.long_position_opened and user_position_state.long_positions == 1 and rsi_6 < StrategyConfig.long_buy_additional_enter:
                log_trade(timestamp, 'Open Long', latest_price, position_size,
                          f"[Additional buy] RSI < {StrategyConfig.long_buy_additional_enter}", user, user_id)

        elif MarketState.trend == "SHORT":
            if user_position_state.long_position_opened and StrategyConfig.use_trend:
                user_position_state.long_position_opened = False
                log_trade(timestamp, 'Close Long', latest_price, user_position_state.long_entry_size, "Trend reversal", user, user_id)

            if user_position_state.short_position_opened and rsi_6 < StrategyConfig.short_sell_rsi_exit:
                user_position_state.short_position_opened = False
                log_trade(timestamp, 'Close Short', latest_price, user_position_state.short_entry_size, f"RSI < {StrategyConfig.short_sell_rsi_exit}", user, user_id)

            if not user_position_state.short_position_opened and rsi_6 > StrategyConfig.short_sell_rsi_enter:
                user_position_state.short_position_opened = True
                log_trade(timestamp, 'Open Short', latest_price, position_size, f"RSI > {StrategyConfig.short_sell_rsi_enter}", user, user_id)

            if user_position_state.short_position_opened and user_position_state.short_positions == 1 and rsi_6 > StrategyConfig.short_sell_additional_enter:
                log_trade(timestamp, 'Open Short', latest_price, position_size,
                          f"[Additional sell] RSI > {StrategyConfig.short_sell_additional_enter}", user, user_id)
