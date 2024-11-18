from order_management import open_position, close_position
from state import *

MAKER_FEE = 0.0002  # 0.02% для мейкеров
TAKER_FEE = 0.0004  # 0.04% для тейкеров

def calculate_commission(size, is_taker=True):
    """Рассчитываем комиссию за сделку."""
    fee_rate = TAKER_FEE if is_taker else MAKER_FEE
    commission = size * fee_rate
    return commission

def log_trade(timestamp, trade_type, price, size, comment):
    # Расчет комиссии за сделку
    commission = calculate_commission(size)
    BacktestState.total_commission += commission

    profit_loss = 0.0

    if "Open" in trade_type:
        PositionState.allocated_capital += size
        BacktestState.current_capital -= size / BacktestConfig.LEVERAGE
        if trade_type == "Open Long":
            PositionState.long_entry_price = price
            open_position('LONG')
        elif trade_type == "Open Short":
            PositionState.short_entry_price = price
            open_position('SHORT')
    elif "Close" in trade_type:
        PositionState.allocated_capital -= size
        BacktestState.current_capital += (size / BacktestConfig.LEVERAGE) + profit_loss
        if trade_type == "Close Long":
            profit_loss = (price - PositionState.long_entry_price) * (size / PositionState.long_entry_price)
            close_position('LONG')
        elif trade_type == "Close Short":
            profit_loss = (PositionState.short_entry_price - price) * (size / PositionState.short_entry_price)
            close_position('SHORT')
        BacktestState.cumulative_profit_loss += profit_loss
        if profit_loss < 0.0:
            BacktestState.unsuccessful_trades += 1
        else:
            BacktestState.successful_trades += 1


    #
    # elif trade_type == "Stop Loss Long":
    #     profit_loss = (price - long_entry_price) * (size / long_entry_price)
    #     current_capital += size / LEVERAGE + profit_loss
    #     cumulative_profit_loss += profit_loss
    #     allocated_capital -= size
    #     unsuccessful_trades += 1
    #
    # elif trade_type == "Stop Loss Short":
    #     profit_loss = (short_entry_price - price) * (size / short_entry_price)
    #     current_capital += size / LEVERAGE + profit_loss
    #     cumulative_profit_loss += profit_loss
    #     allocated_capital -= size
    #     unsuccessful_trades += 1

    # if current_capital > INITIAL_CAPITAL:
    #     farmed_money += current_capital - INITIAL_CAPITAL
    #     current_capital = INITIAL_CAPITAL

    # if current_capital < INITIAL_CAPITAL * 0.5:
    #     farmed_money -= INITIAL_CAPITAL * 0.5
    #     current_capital += INITIAL_CAPITAL * 0.5

    # Добавляем комиссию в лог, но не меняем баланс
    BacktestState.trade_log.append({
        'timestamp': timestamp,
        'trade_type': trade_type,
        'price': price,
        'size': size,
        'margin': size / BacktestConfig.LEVERAGE,
        'current_balance': round(BacktestState.current_capital, 2),
        'allocated_capital': round(PositionState.allocated_capital, 2),
        'comment': comment,
        'profit_loss': round(profit_loss, 2),
        'cumulative_profit_loss': round(BacktestState.cumulative_profit_loss, 2),
        'commission': round(commission, 2),  # Добавляем комиссию
    })
    log(f"{timestamp} {trade_type} ({comment}) {price}@{size} | {round(BacktestState.current_capital, 2)} | {round(BacktestState.cumulative_profit_loss)}")

    if BacktestConfig.enabled:
        log(f"{timestamp}: {trade_type} at {price}, Size: {size:.5f}, "
              f"Balance: {BacktestState.current_capital:.8f}, Allocated Capital: {PositionState.allocated_capital:.8f}, "
              f"Profit/Loss: {profit_loss:.8f}, Cumulative P/L: {BacktestState.cumulative_profit_loss:.8f}, "
              f"Commission: {commission:.8f}, Comment: {comment}")
