import datetime

from logger_output import log
from order_management import open_position, close_position
from formatting import format_number, format_price


def calculate_commission(size, is_taker=True):
    MAKER_FEE = 0.0002  # 0.02%
    TAKER_FEE = 0.0004  # 0.04%

    fee_rate = TAKER_FEE if is_taker else MAKER_FEE
    commission = size * fee_rate
    return commission

def update_balance_and_stats(timestamp, trade_type, price, size, comment, profit_loss, leverage, strategy):
    commission = calculate_commission(size)

    strategy_stats = strategy.stats
    strategy_stats.total_commission += commission
    strategy_stats.cumulative_profit_loss += profit_loss

    if "Open" in trade_type:
        strategy_stats.current_capital -= size
        strategy_stats.allocated_capital += size
    elif "Close" in trade_type:
        strategy_stats.current_capital += size + profit_loss
        strategy_stats.allocated_capital = 0

        if profit_loss < 0.0:
            strategy_stats.unsuccessful_trades += 1
        else:
            strategy_stats.successful_trades += 1

    strategy_stats.append_trade(strategy.user_id, strategy.strategy_id, {
        'timestamp': timestamp,
        'trade_type': trade_type,
        'price': price,
        'size': size,
        'leverage': leverage,
        'full_size': size * leverage,
        'current_balance': round(strategy_stats.current_capital, 2),
        'allocated_capital': round(strategy_stats.allocated_capital, 2),
        'comment': comment,
        'profit_loss': round(profit_loss, 2),
        'cumulative_profit_loss': round(strategy_stats.cumulative_profit_loss, 2),
        'commission': round(commission, 2),
    })


def log_trade(timestamp, trade_type, price, size, comment, strategy, user):
    profit_loss = 0.0
    position_state = strategy.position_state

    leverage = strategy.strategy_config.leverage
    full_position_size = size * leverage

    if "Open" in trade_type:
        if trade_type == "Open Long":
            open_position('LONG', position_state, size, leverage)
        elif trade_type == "Open Short":
            open_position('SHORT', position_state, size, leverage)
        position_state.open(trade_type, size, price, leverage)
    elif "Close" in trade_type:
        if trade_type == "Close Long":
            close_position('LONG', position_state, size)
        elif trade_type == "Close Short":
            close_position('SHORT', position_state, size)
        profit_loss, entry_price = position_state.close_all(trade_type, price)

    formatted_timestamp = timestamp.strftime('%d.%m.%Y %H:%M')
    update_balance_and_stats(formatted_timestamp, trade_type, price, size, comment, profit_loss, leverage, strategy)

    strategy.store_state()

    # price_color = "🍏" if "Long" in trade_type else "🍎"
    action = "🏁" if "Close" in trade_type else "🛒"

    pnl_symbol = '🔺' if profit_loss >= 0 else '🔻'
    pnl_icon = '🚀' if profit_loss >= 0 else '🥀'
    is_trade_close = "Close" in trade_type

    price_or_price_change = f"`{price:,.0f}$`    " if not is_trade_close else f"`{format_price(entry_price)} → {price:,.0f}$`"

    def fix_timestamp(timestamp):
        dt = datetime.datetime.strptime(timestamp, "%d.%m.%Y %H:%M")
        # Формируем строку без года
        formatted_timestamp = dt.strftime("%d.%m %H:%M")
        return formatted_timestamp

    formatted_signal = (
        f"🎰 *{strategy.strategy_config.name} trade* ⚡\n"
        f"{action} {trade_type} | 🕓 {fix_timestamp(formatted_timestamp)}\n"
        # f"\n"
        f"💰 {price_or_price_change} | 📦 `{full_position_size:,.0f}$` (`{leverage}x`)\n"
        + (f"{pnl_icon} `{format_number(profit_loss)}` {pnl_symbol} | " if is_trade_close else '') +
        f"💬 {comment}\n"
    )

    log(f"{formatted_signal}", user.user_id)