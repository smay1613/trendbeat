from prod.config import BacktestConfig
from prod.logger_output import log


class BacktestState:
    current_capital = BacktestConfig.INITIAL_CAPITAL
    successful_trades = 0
    unsuccessful_trades = 0

    max_drawdown = 0
    max_balance = 0
    cumulative_profit_loss = 0
    total_commission = 0.0
    farmed_money = 0.0
    trade_log = []

    @staticmethod
    def dump():
        log(f"Текущий капитал: {BacktestState.current_capital:.2f}")
        log(f"Общая прибыль/убыток: {BacktestState.cumulative_profit_loss:.2f}")
        log(f"Успешные сделки: {BacktestState.successful_trades}")
        log(f"Неуспешные сделки: {BacktestState.unsuccessful_trades}")
        log(f"Комиссия: {BacktestState.total_commission:.2f}")
        log(f"Максимальная просадка: {BacktestState.max_drawdown:.2f}%")


class PositionState:
    long_position_opened = False
    short_position_opened = False
    long_entry_price = 0
    short_entry_price = 0

    allocated_capital = 0
    position_qty = 0.0


class MarketState:
    trend = None
    trend_type = None
