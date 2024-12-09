from config import BacktestConfig
from logger_output import log
from database_helper import DatabaseHelper


class UserBalance:
    def __init__(self):
        self.current_capital = BacktestConfig.INITIAL_CAPITAL
        self.allocated_capital = 0
        self.cumulative_profit_loss = 0
        self.total_commission = 0.0

    def dump(self):
        pnl_color = "🔴" if self.cumulative_profit_loss < 0 else "🟢"
        pnl_symbol = '🔺' if self.cumulative_profit_loss >= 0 else '🔻'
        # Формируем сообщение
        def format_number(number):
            return f'{number:,.2f}'.rstrip('0').rstrip('.') + '$'

        message = (
            "🏦 *Balance*\n\n"
            f"💰 *Current Capital:*      `{format_number(self.current_capital)}`\n"
            f"💼 *Allocated Capital:*    `{format_number(self.allocated_capital)}`\n"
            f"{pnl_color} *Cumulative P&L:*       `{format_number(self.cumulative_profit_loss)}` {pnl_symbol}\n"
            f"🛠️ *Exchange Commissions:* `{'-' if self.total_commission > 0 else ''}{format_number(self.total_commission)}`"
        )
        return message

    def load(self, row):
        for key, value in row.items():
            setattr(self, key, value)

    def store(self, user_id):

        data = self.__dict__
        data['user_id'] = user_id
        DatabaseHelper.store("user_balance", data)

class UserStats:
    def __init__(self):
        self.successful_trades = 0
        self.unsuccessful_trades = 0
        self.trade_logs = []

    def load(self, row):
        for key, value in row.items():
            setattr(self, key, value)

    def store(self, user_id):
        data = self.__dict__
        data['user_id'] = user_id
        del data["trade_logs"]
        DatabaseHelper.store("user_stats", data)

    def append_trade(self, user_id, trade_params):
        self.trade_logs.append(trade_params)
        trade_params["user_id"] = user_id
        DatabaseHelper.store("trade_logs", trade_params)

    # @staticmethod
    # def dump():
    #     log(f"Текущий капитал: {BacktestState.current_capital:.2f}")
    #     log(f"Общая прибыль/убыток: {BacktestState.cumulative_profit_loss:.2f}")
    #     log(f"Успешные сделки: {BacktestState.successful_trades}")
    #     log(f"Неуспешные сделки: {BacktestState.unsuccessful_trades}")
        # log(f"Комиссия: {BacktestState.total_commission:.2f}")
        # log(f"Максимальная просадка: {BacktestState.max_drawdown:.2f}%")


class PositionState:
    def __init__(self):
        self.long_position_opened = False
        self.short_position_opened = False

        self.long_entry_price = 0
        self.long_entry_size = 0
        self.long_positions = 0

        self.short_entry_price = 0
        self.short_entry_size = 0
        self.short_positions = 0

        self.position_qty = 0.0

    def dump(self):
        message = "🔑 *Positions*\n\n"

        if self.long_position_opened:
            multiplier = f" x{self.long_positions}" if self.long_positions > 1 else ""
            message += (
                f"📈 *Long* {multiplier}: `{self.long_entry_price:,.2f}$`\n"
                f"📦️ *Size:* `{self.long_entry_size:,.2f}$`\n"
            )

        if self.short_position_opened:
            multiplier = f" (x{self.short_positions})" if self.short_positions > 1 else ""
            message += (
                f"📉 *Short*{multiplier}: `{self.short_entry_price:,.2f}$`\n"
                f"▫️ *Size:* `{self.short_entry_size:,.2f,}$`\n"
            )

        if not self.long_position_opened and not self.short_position_opened:
            message += "💤 No active positions\n"

        return message

    def close_all(self, type, price):
        profit_loss = 0

        if "long" in type.lower():
            profit_loss = (price - self.long_entry_price) * (self.long_entry_size / self.long_entry_price)
            self.long_positions = 0
            self.long_entry_price = 0
            self.long_entry_size = 0
        elif "short" in type.lower():
            profit_loss = (self.short_entry_price - price) * (self.short_entry_size / self.short_entry_price)
            self.short_positions = 0
            self.short_entry_price = 0
            self.short_entry_size = 0

        return profit_loss

    def open(self, type, size, price):
        if "long" in type.lower():
            self.long_positions += 1
            self.long_entry_size += size
            self.long_entry_price += price
            self.long_entry_price = self.long_entry_price / self.long_positions
        elif "short" in type.lower():
            self.short_positions += 1
            self.short_entry_size += size
            self.short_entry_price += price
            self.short_entry_price = self.short_entry_price / self.short_positions

    def load(self, row):
        for key, value in row.items():
            setattr(self, key, value == "True")

    def store(self, user_id):
        data = self.__dict__
        data['user_id'] = user_id
        DatabaseHelper.store("position_state", data)

class MarketState:
    trend = None
    trend_type = None
