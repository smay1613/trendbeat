from trade_drop import log_trade
from logger_output import log
from state import MarketState


def is_high_volume(row):
    return float(row['volume']) > row['Average_Volume']

# def calculate_position_size(price, atr):
#     """Расчет размера позиции на основе капитала и риска."""
#     # risk_per_trade = MAX_RISK_PER_TRADE * current_capital
#     position_size = 300.0 #risk_per_trade / atr  # учитываем волатильность
#     return position_size * BacktestConfig.LEVERAGE

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
            is_downtrend = MarketState.trend == 'SHORT'
            if MarketState.trend != old_trend:
                log(f"⚠️ *{MarketState.trend_type.capitalize()} {'downtrend' if is_downtrend else 'uptrend'} started!* {'📉' if is_downtrend else '📈'}",
                    user=user_id)
            elif MarketState.trend_type != old_trend_type:
                log(f"⚠️ *{'Downtrend' if is_downtrend else 'Uptrend'} becomes {MarketState.trend_type.lower()}!* {'📉📉📉' if is_downtrend else '📈📈📈'}",
                    user=user_id)

    return MarketState.trend, MarketState.trend_type


def trade_logic(row, timestamp, latest_price, strategy, user):
    rsi_6 = row['RSI_6']
    # atr = row['ATR']
    adx = row['ADX']
    # macd = row['MACD']
    # Calculate max drawdown

    strategy_config = strategy.strategy_config

    # Trade Logic
    if adx > strategy_config.min_adx and (not strategy_config.high_volume_only or is_high_volume(row)):
        position_size = strategy_config.position_size

        if not strategy_config.allow_weak_trend and MarketState.trend_type != "STRONG":
            # log(f"{timestamp} Trend is not strong, no decision")
            return

        position_state = strategy.position_state

        if MarketState.trend == "LONG":
            if position_state.short_position_opened and strategy_config.close_on_trend_reverse:
                position_state.short_position_opened = False
                log_trade(timestamp, 'Close Short', position_state.short_entry_size, "Trend reversal", strategy, user)

            if position_state.long_position_opened and rsi_6 > strategy_config.long_buy_rsi_exit:
                position_state.long_position_opened = False
                log_trade(timestamp, 'Close Long', position_state.long_entry_size, f"RSI > {strategy_config.long_buy_rsi_exit}", strategy, user)

            if not position_state.long_position_opened and rsi_6 < strategy_config.long_buy_rsi_enter:
                position_state.long_position_opened = True
                log_trade(timestamp, 'Open Long', position_size, f"RSI < {strategy_config.long_buy_rsi_enter}", strategy, user)

            if position_state.long_position_opened and position_state.long_positions == 1 and rsi_6 < strategy_config.long_buy_additional_enter:
                log_trade(timestamp, 'Open Long', position_size,
                          f"DCA RSI < {strategy_config.long_buy_additional_enter}", strategy, user)

        elif MarketState.trend == "SHORT":
            if position_state.long_position_opened and strategy_config.close_on_trend_reverse:
                position_state.long_position_opened = False
                log_trade(timestamp, 'Close Long', position_state.long_entry_size, "Trend reversal", strategy, user)

            if position_state.short_position_opened and rsi_6 < strategy_config.short_sell_rsi_exit:
                position_state.short_position_opened = False
                log_trade(timestamp, 'Close Short', position_state.short_entry_size, f"RSI < {strategy_config.short_sell_rsi_exit}", strategy, user)

            if not position_state.short_position_opened and rsi_6 > strategy_config.short_sell_rsi_enter:
                position_state.short_position_opened = True
                log_trade(timestamp, 'Open Short', position_size, f"RSI > {strategy_config.short_sell_rsi_enter}", strategy, user)

            if position_state.short_position_opened and position_state.short_positions == 1 and rsi_6 > strategy_config.short_sell_additional_enter:
                log_trade(timestamp, 'Open Short', position_size,
                          f"DCA RSI > {strategy_config.short_sell_additional_enter}", strategy, user)
