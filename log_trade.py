import datetime

from order_management import open_position, close_position
from state import *

MAKER_FEE = 0.0002  # 0.02% для мейкеров
TAKER_FEE = 0.0004  # 0.04% для тейкеров

def calculate_commission(size, is_taker=True):
    """Рассчитываем комиссию за сделку."""
    fee_rate = TAKER_FEE if is_taker else MAKER_FEE
    commission = size * fee_rate
    return commission

def update_balance_and_stats(timestamp, trade_type, price, size, comment, profit_loss, user_data, user_id):
    commission = calculate_commission(size)

    user_balance = user_data.balance
    user_balance.total_commission += commission
    user_balance.cumulative_profit_loss += profit_loss

    user_stats = user_data.stats

    if "Open" in trade_type:
        user_balance.current_capital -= size / BacktestConfig.LEVERAGE
        user_balance.allocated_capital += size
    elif "Close" in trade_type:
        user_balance.current_capital += (size / BacktestConfig.LEVERAGE) + profit_loss
        user_balance.allocated_capital = 0

        if profit_loss < 0.0:
            user_stats.unsuccessful_trades += 1
        else:
            user_stats.successful_trades += 1
        user_stats.store(user_id)

    user_balance.store(user_id)

    user_stats.append_trade({
        'timestamp': timestamp,
        'trade_type': trade_type,
        'price': price,
        'size': size,
        # 'margin': size / BacktestConfig.LEVERAGE,
        'current_balance': round(user_balance.current_capital, 2),
        'allocated_capital': round(user_balance.allocated_capital, 2),
        'comment': comment,
        'profit_loss': round(profit_loss, 2),
        'cumulative_profit_loss': round(user_balance.cumulative_profit_loss, 2),
        'commission': round(commission, 2),
    })
#

        # log(f"{timestamp} {trade_type} ({comment}) {price}@{size}\n"
        #     f"{round(BacktestState.current_capital, 2)}\n"
        #     f"{round(BacktestState.cumulative_profit_loss)}\n")


def log_trade(timestamp, trade_type, price, size, comment, user_data, user_id):
    profit_loss = 0.0
    user_position_state = user_data.position_state

    if "Open" in trade_type:
        if trade_type == "Open Long":
            open_position('LONG', user_position_state)
        elif trade_type == "Open Short":
            open_position('SHORT', user_position_state)
        user_position_state.open(trade_type, size, price)
    elif "Close" in trade_type:
        if trade_type == "Close Long":
            close_position('LONG', user_position_state)
        elif trade_type == "Close Short":
            close_position('SHORT', user_position_state)
        profit_loss = user_position_state.close_all(trade_type, price)

    update_balance_and_stats(timestamp, trade_type, price, size, comment, profit_loss, user_data, user_id)

    user_position_state.store(user_id)

    formatted_timestamp = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    # Определяем цвет/стиль для цены и размера
    price_color = "🟩" if "Long" in trade_type else "🔴"  # Зеленый для покупки, красный для продажи
    action = "🏁" if "Close" in trade_type else "🛒"

    # Формируем красиво отформатированную строку
    formatted_signal = (
        f"⚡ *Trade* ⚡\n"
        f"🕰️ *Timestamp:* {formatted_timestamp}\n"
        f"🔑 *Action:* {action} {trade_type} {price_color}\n"
        f"📦 *Price:* `{price:,.0f}$`\n"
        f"📦 *Size:* `{size:,.0f}$`\n"
        f"💬 *Comment:* {comment}\n"
    )
    #
    log(f"{formatted_signal}", user_id)
    #     f"{round(BacktestState.current_capital, 2)}\n"
    #     f"{round(BacktestState.cumulative_profit_loss)}\n")

        # BacktestState.cumulative_profit_loss += profit_loss
        # if profit_loss < 0.0:
        #     BacktestState.unsuccessful_trades += 1
        # else:
        #     BacktestState.successful_trades += 1


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

    # if BacktestConfig.enabled:
    #     log(f"{timestamp}: {trade_type} at {price}, Size: {size:.5f}, "
    #           f"Balance: {BacktestState.current_capital:.8f}, Allocated Capital: {PositionState.allocated_capital:.8f}, "
    #           f"Profit/Loss: {profit_loss:.8f}, Cumulative P/L: {BacktestState.cumulative_profit_loss:.8f}, "
    #           f"Commission: {commission:.8f}, Comment: {comment}")
