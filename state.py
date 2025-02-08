import copy
import datetime
import random

from config import BacktestConfig, StrategyConfig
from database_helper import DatabaseHelper, get_database_helper, DatabaseConfig
from formatting import format_price, format_number
from logger_output import log, log_error
from trade_drop import calculate_pnl

database_helper = get_database_helper()

class StrategyStats:
    def __init__(self):
        self.successful_trades = 0
        self.unsuccessful_trades = 0
        self.trade_logs = []
        self.positions_history = []

        self.current_capital = BacktestConfig.INITIAL_CAPITAL
        self.allocated_capital = 0
        self.cumulative_profit_loss = 0
        self.total_commission = 0.0

    def load(self, row):
        for key, value in row.items():
            setattr(self, key, value)

    def store(self, strategy_id):
        data = copy.deepcopy(self.__dict__)
        data['strategy_id'] = strategy_id
        del data["trade_logs"]
        del data['successful_trades']
        del data['unsuccessful_trades']
        del data['positions_history']
        database_helper.store("strategy_balance", data)

        stats_data = {'strategy_id': strategy_id, 'successful_trades': self.successful_trades,
                      'unsuccessful_trades': self.unsuccessful_trades}
        database_helper.store("strategy_stats", stats_data)

    def append_trade(self, user_id, strategy_id, trade_params):
        self.trade_logs.append(trade_params)
        trade_params["user_id"] = user_id
        trade_params["strategy_id"] = strategy_id
        database_helper.store("trade_logs", trade_params)
        self.positions_history = self.get_all_positions()

    def dump_short(self):
        pnl_symbol = '🔺' if self.cumulative_profit_loss >= 0 else '🔻'
        return f"💰 *Balance*: `{format_number(self.current_capital + self.allocated_capital)}` | `{format_number(self.cumulative_profit_loss)}` {pnl_symbol}\n"

    def dump(self):
        pnl_color = "🔴" if self.cumulative_profit_loss < 0 else "🟢"
        pnl_symbol = '🔺' if self.cumulative_profit_loss >= 0 else '🔻'

        win_rate = (self.successful_trades / max(1, (self.successful_trades + self.unsuccessful_trades))) * 100

        message = (
            "🏦 *Balance*\n\n"
            f"💰 *Total Capital:*      `{format_number(self.current_capital + self.allocated_capital)}`\n"
            f"💰 *Free Capital:*      `{format_number(self.current_capital)}`\n"
            f"💼 *Allocated Capital:*    `{format_number(self.allocated_capital)}`\n"
            f"{pnl_color} *Cumulative P&L:*       `{format_number(self.cumulative_profit_loss)}` {pnl_symbol}\n"
            f"🛠️ *Exchange Commissions:* `{'-' if self.total_commission > 0 else ''}{format_number(self.total_commission)}`\n"
            f"\n🧮 *Trade Statistics*\n\n"
            f"🌟 *Successful Trades:*     `{self.successful_trades}`\n"
            f"💔 *Failed Trades:*            `{self.unsuccessful_trades}`\n"
            f"🥇 *Win Rate:*                     `{format_number(win_rate, dollars=False)}%`"
        )
        return message

    def load_history(self, history_rows):
        self.trade_logs = history_rows
        self.positions_history = self.get_all_positions()

    def dump_history(self, begin=1, step=5):
        header = "📜 *Orders History*\n"
        if not len(self.trade_logs):
            return header + "💤 No orders were created yet\n"

        begin -= 1
        positions = self.positions_history[begin * step:begin * step + step]
        separator = '\n──────────\n'

        return header + separator + f"{separator}".join(positions)

    def get_all_positions(self):
        position_counter = 0
        open_position_trade = None
        dca_trade = None
        close_trade = None
        positions = []
        for trade in self.trade_logs:
            if "Open" in trade['trade_type']:
                if not open_position_trade:
                    open_position_trade = trade
                elif not dca_trade:
                    dca_trade = trade
            elif "Close" in trade['trade_type']:
                close_trade = trade
                position_counter += 1
                msg = self.dump_position(open_position_trade, dca_trade, close_trade, position_counter)
                positions.append(f"{msg}")
                open_position_trade = None
                dca_trade = None
                close_trade = None

        if not close_trade and open_position_trade:
            position_counter += 1
            msg = self.dump_position(open_position_trade, dca_trade, close_trade, position_counter)
            positions.append(f"{msg}")
        positions = list(reversed(positions))
        return positions

    def dump_position(self, open_trade, dca_trade, close_trade, position_counter):
        if not open_trade:
            log("Error: User has inconsistent trades!")
            return

        position_type = 'Active' if not close_trade else 'Closed'
        is_long_position = "Long" in open_trade['trade_type']

        def fix_timestamp(timestamp):
            dt = datetime.datetime.strptime(timestamp, "%d.%m.%Y %H:%M")
            # Формируем строку без года
            formatted_timestamp = dt.strftime("%d.%m %H:%M")
            return formatted_timestamp

        header = (
           f"💹 *Position {position_counter}* (_{position_type}_) | {'🍏 Long' if is_long_position else '🍎 Short'}\n"
        )

        total_comission = open_trade['commission'] + (dca_trade['commission'] if dca_trade else 0) \
                           + (close_trade['commission'] if close_trade else 0)
        total_size = open_trade['full_size'] + (dca_trade['full_size'] if dca_trade else 0)

        open_trade_msg = (
           f"🎯 *Open* | 🕓 {fix_timestamp(open_trade['timestamp'])} | 💬 {open_trade['comment']}\n"
        )
        price_change = f"💰 `{format_price(open_trade['price'])}` 🛒"

        if dca_trade:
            dca_message = (
                f"🎯 *DCA*   | 🕓 {fix_timestamp(dca_trade['timestamp'])} | 💬 {dca_trade['comment']}\n"
            )
            price_change += f" → `{format_price(dca_trade['price'])}` 🔄"
        else:
            dca_message = ''

        if close_trade:
            profit_loss = close_trade['profit_loss']
            pnl_symbol = '🔺' if profit_loss >= 0 else '🔻'
            pnl_icon = '🚀' if profit_loss >= 0 else '🥀'
            close_message = (
                f"🏁 *Close* | 🕓 {fix_timestamp(close_trade['timestamp'])} | 💬 {close_trade['comment']}\n"
            )
            pnl = f"{pnl_icon} `{format_price(close_trade['profit_loss'], diff=True)}` {pnl_symbol} | 🌟 `{format_price(close_trade['cumulative_profit_loss'], diff=True)}`\n"
            price_change += f" → `{format_price(close_trade['price'])}` 🏁"
        else:
            close_message = ''
            pnl = ''

        full_msg = (
            f"{header}"
            f"{pnl}"
            f"{price_change}\n"
            f"📦 `{format_number(total_size)}` ({open_trade['leverage']}x) | 🛠 `{format_number(total_comission)}`\n\n"
            f"{open_trade_msg}"
            f"{dca_message}"
            f"{close_message}"
        )

        return full_msg

class PositionState:
    def __init__(self):
        self.long_position_opened = False
        self.short_position_opened = False

        self.long_entry_price = 0
        self.long_entry_size = 0
        self.long_entry_full_size = 0
        self.long_positions = 0

        self.short_entry_price = 0
        self.short_entry_size = 0
        self.short_entry_full_size = 0
        self.short_positions = 0

        self.position_qty = 0.0
        self.leverage = 0


    def dump_short(self):
        message = ""
        current_pnl = calculate_pnl(self)
        # current_pnl_color = "🔴" if current_pnl < 0 else "🟢"
        current_pnl_symbol = '🔺' if current_pnl >= 0 else '🔻'

        if self.long_position_opened:
            multiplier = f" (x{self.long_positions})" if self.long_positions > 1 else ""
            message += (
                f"🍏 *Long* {multiplier} | `{format_price(self.long_entry_price)}` | `{format_number(current_pnl)}` {current_pnl_symbol}\n"
            )

        if self.short_position_opened:
            multiplier = f" (x{self.short_positions})" if self.short_positions > 1 else ""
            message += (
                f"🍎 *Short* {multiplier} | `{format_price(self.short_entry_price)}` | `{format_number(current_pnl)}` {current_pnl_symbol}\n"
            )

        if not self.long_position_opened and not self.short_position_opened:
            message += "💤 *No active positions*\n"

        return message

    def dump(self):
        message = "💼 *Open Positions*\n\n"
        current_pnl = calculate_pnl(self)
        current_pnl_color = "🔴" if current_pnl < 0 else "🟢"
        current_pnl_symbol = '🔺' if current_pnl >= 0 else '🔻'

        if self.long_position_opened:
            multiplier = f" (x{self.long_positions})" if self.long_positions > 1 else ""

            message += (
                f"🍏 *Long* {multiplier}\n"
                f"💵 *Entry*: `{format_price(self.long_entry_price)}`\n"
                f"📦️ *Size*: `{format_price(self.long_entry_size)} x{self.leverage}` (`{format_price(self.long_entry_full_size)}`)\n"
                f"{current_pnl_color} *P&L*:  `{format_number(current_pnl)}` {current_pnl_symbol}\n"
            )

        if self.short_position_opened:
            multiplier = f" (x{self.short_positions})" if self.short_positions > 1 else ""
            message += (
                f"🍎 *Short* {multiplier}\n"
                f"💵 *Entry*: `{format_price(self.short_entry_price)}`\n"
                f"📦️ *Size*: `{format_price(self.short_entry_size)} x{self.leverage}` (`{format_price(self.short_entry_full_size)}`)\n"
                f"{current_pnl_color} *P&L*:  `{format_number(current_pnl)}` {current_pnl_symbol}\n"
            )

        if not self.long_position_opened and not self.short_position_opened:
            message += "💤 No active positions\n"

        return message

    def close_all(self, type, price):
        profit_loss = 0

        if "long" in type.lower():
            entry_price = self.long_entry_price
            profit_loss = (price - self.long_entry_price) * (self.long_entry_full_size / self.long_entry_price)
            self.long_positions = 0
            self.long_entry_price = 0
            self.long_entry_size = 0
            self.long_entry_full_size = 0
            self.long_position_opened = False
        elif "short" in type.lower():
            entry_price = self.short_entry_price
            profit_loss = (self.short_entry_price - price) * (self.short_entry_full_size / self.short_entry_price)
            self.short_positions = 0
            self.short_entry_price = 0
            self.short_entry_size = 0
            self.short_entry_full_size = 0
            self.short_position_opened = False

        self.leverage = 0
        self.position_qty = 0

        return round(profit_loss, 2), entry_price

    def open(self, type, size, price, leverage):
        self.leverage = leverage

        if "long" in type.lower():
            self.long_positions += 1
            self.long_entry_full_size += size * leverage
            self.long_entry_size += size
            self.long_entry_price += price
            self.long_entry_price = self.long_entry_price / self.long_positions
        elif "short" in type.lower():
            self.short_positions += 1
            self.short_entry_full_size += size * leverage
            self.short_entry_size += size
            self.short_entry_price += price
            self.short_entry_price = self.short_entry_price / self.short_positions

    def load(self, row):
        for key, value in row.items():
            setattr(self, key, value)

    def store(self, strategy_id):
        data = self.__dict__
        data['strategy_id'] = strategy_id
        database_helper.store("strategy_position_state", data)

class MarketState:
    trend = None
    trend_type = None

class UserSettings:
    def __init__(self):
        self.market_overview_enabled = True
        self.alerts_enabled = True
        self.overview_settings_display = {
            "price": True,
            "volume": True,
            "rsi": True,
            "trend": True,
            "ema": True,
            "bands": True,
            "support": True,
            "resistance": True,
            "dominance": True,
            "sentiment": True,
            "session": True
        }
        self.overview_sections = {
            "price": True,
            "trend": True,
            "support_resistance": False,
            "sentiment": False
        }

    def load(self, row, overview_sections, overview_display):
        for key, value in row.items():
            setattr(self, key, value)

        self.overview_sections.update(overview_sections)
        self.overview_settings_display.update(overview_display)

    def store_overview_sections(self, user_id):
        data = copy.deepcopy(self.overview_sections)
        data['user_id'] = user_id
        database_helper.store("overview_sections_config", data)

    def store_overview_settings_display(self, user_id):
        data = copy.deepcopy(self.overview_settings_display)
        data['user_id'] = user_id
        database_helper.store("overview_display_config", data)

    def toggle(self, config, enabled):
        if config == "market_overview_enabled":
            self.market_overview_enabled = enabled
        elif config == "alerts_enabled":
            self.alerts_enabled = enabled

    def store(self, user_id):
        data = copy.deepcopy(self.__dict__)
        del data['overview_settings_display']
        del data['overview_sections']
        data['user_id'] = user_id

        database_helper.store("user_config", data)

class UserStrategies:
    def __init__(self, user_id):
        self.user_id = user_id
        self.strategies = {}
        # active/deactivated

    def get_strategy(self, id):
        return self.strategies[id] if id in self.strategies else None

    def setup_default_strategies(self):
        extreme_rsi_strategy = StrategyConfig("TrendBeat Aggressive")
        extreme_rsi_strategy.setup_risk_checks(min_adx=15, allow_weak_trend=False, close_on_trend_reverse=True, high_volume_only=True)
        extreme_rsi_strategy.setup_long_position(enter=62, additional_enter=46, exit=78)
        extreme_rsi_strategy.setup_short_position(enter=38, additional_enter=52, exit=28)
        extreme_rsi_strategy.setup_position_settings(position_size=150.0)

        neutral_rsi_strategy = StrategyConfig("TrendBeat Neutral")
        neutral_rsi_strategy.setup_risk_checks(min_adx=15, allow_weak_trend=False, close_on_trend_reverse=True, high_volume_only=True)
        neutral_rsi_strategy.setup_long_position(enter=56, additional_enter=36, exit=72)
        neutral_rsi_strategy.setup_short_position(enter=58, additional_enter=68, exit=28)
        neutral_rsi_strategy.setup_position_settings(position_size=150.0)

        return [TradeStrategy(self.user_id, extreme_rsi_strategy), TradeStrategy(self.user_id, neutral_rsi_strategy)]

    def dump(self, risks, rsi):
        header = "🤖 *Active strategies*\n\n" + '──────────\n'

        msg = header
        if len(self.strategies) == 0:
            msg += "💤 No active strategies"
            return msg

        for strategy in self.strategies.values():
            msg += self.dump_strategy(strategy, risks, rsi)

        return msg

    def dump_strategy(self, strategy, risks, rsi, separator=True):
        msg = ""
        msg += f"🎰 *{strategy.strategy_config.name}*\n\n"
        msg += strategy.stats.dump_short()
        msg += strategy.position_state.dump_short()
        msg += (strategy.strategy_config.dump(risks=risks, long_rsi=rsi, short_rsi=rsi)
                + ('──────────\n' if separator else ''))
        return msg

    def register_default_strategies(self):
        default_strategies = self.setup_default_strategies()
        for strategy in default_strategies:
            strategy.store()
            self.strategies[strategy.strategy_id] = strategy

    def load(self, user_id, user_strategies, position_states, balances, stats, strategy_configs, history):
        if len(user_strategies) == 0:
            self.register_default_strategies()
            return

        if not (len(stats) == len(position_states) == len(balances)):
            print(f"Inconsistent user strategies! User = {user_id}")
            return

        for strategy_id in [data['strategy_id'] for data in user_strategies[user_id]]:
            config = StrategyConfig(None)
            config.load(strategy_configs[strategy_id])
            strategy = TradeStrategy(user_id, config, strategy_id)
            strategy.load(stats[strategy_id], balances[strategy_id], position_states[strategy_id], history[strategy_id] if strategy_id in history else [])
            self.strategies[strategy_id] = strategy


class TradeStrategy:
    def __init__(self, user_id, config, strategy_id=None):
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.stats = StrategyStats()
        self.position_state = PositionState()
        self.strategy_config = config

    def store_state(self):
        try:
            self.stats.store(self.strategy_id)
            self.position_state.store(self.strategy_id)
        except Exception as e:
            log_error(f"Error during storing strategy state: {e}")

    def store(self):
        if not self.strategy_id:
            data = {"user_id": self.user_id}
            response = database_helper.store("user_strategies", data)
            if response:
                generated_id = response[0]['strategy_id']
                self.strategy_id = generated_id
            else:
                if not DatabaseConfig.store_to_db:
                    self.strategy_id = random.randint(1, 10000)
                else:
                    raise Exception(f"Failed to insert strategy: {response.error}")

        self.stats.store(self.strategy_id)
        self.strategy_config.store(self.strategy_id)
        self.position_state.store(self.strategy_id)

    def load(self, stats, balance, state, history):
        self.stats.load(stats)
        self.stats.load(balance)
        self.stats.load_history(history)
        self.position_state.load(state)


class UserData:
    def __init__(self, user_id):
        self.user_id = user_id
        self.user_settings = UserSettings()
        self.strategies = UserStrategies(user_id)

    def load(self, user_config_row, user_strategies, position_states,
             balances, stats, strategy_configs, history,
             overview_sections, overview_display):
        if user_config_row:
            self.user_settings.load(user_config_row, overview_sections, overview_display)

        self.strategies.load(self.user_id, user_strategies, position_states, balances, stats, strategy_configs, history)


class UserManager:
    def __init__(self):
        self.users = {}
        self.load_users()

    def exists(self, user_id):
        return user_id in self.users

    def validate(self, user_id):
        return self.exists(user_id)

    def get(self, user_id):
        return self.users[user_id]

    def add_user_if_not_exist(self, user_id, username):
        if not self.exists(user_id):
            database_helper.store("users", {"user_id": user_id, "username": username})
            self.users[user_id] = UserData(user_id)
            self.users[user_id].strategies.register_default_strategies()

    def load_users(self):
        users = database_helper.get_table_data("users")
        for user in users:
            self.users[user['user_id']] = UserData(user_id=user['user_id'])

        self.load_user_data()

    def load_user_data(self):
        def separate(separate_by_key, rows, unique=True):
            entity_to_data = {}
            for row in rows:
                if unique:
                    entity_to_data[row[separate_by_key]] = row
                else:
                    if row[separate_by_key] not in entity_to_data:
                        entity_to_data[row[separate_by_key]] = []
                    entity_to_data[row[separate_by_key]].append(row)

            return entity_to_data

        db = database_helper.get_client()

        config_response = db.table("user_config").select("user_id, market_overview_enabled, alerts_enabled").execute()
        db = database_helper.get_client()
        user_strategies = db.table("user_strategies").select("user_id, strategy_id").execute()
        stats_response = db.table("strategy_stats").select(
            "strategy_id, successful_trades, unsuccessful_trades").execute()
        position_response = db.table("strategy_position_state").select("""
            strategy_id, long_position_opened, short_position_opened, 
            long_entry_price, long_entry_size, long_entry_full_size, long_positions,
            short_entry_price, short_entry_size, short_entry_full_size, short_positions, 
            position_qty, leverage
        """).execute()
        balance_response = db.table("strategy_balance").select("""
            strategy_id, current_capital, allocated_capital, cumulative_profit_loss, total_commission
        """).execute()
        strategy_config_response = db.table("strategy_config").select("""
        strategy_id, name, high_volume_only, position_size, long_buy_rsi_enter, long_buy_additional_enter, long_buy_rsi_exit,
        short_sell_rsi_enter, short_sell_additional_enter, short_sell_rsi_exit,
        min_adx, allow_weak_trend, close_on_trend_reverse, leverage
        """).execute()
        trade_logs_response = db.table("trade_logs").select("""
            id, user_id, strategy_id, timestamp, trade_type, price, size, leverage, full_size, 
            current_balance, allocated_capital, comment, profit_loss, cumulative_profit_loss, commission
        """).execute()
        overview_sections = db.table("overview_sections_config").select("""
            user_id, price, trend, support_resistance, sentiment
        """).execute()
        overview_settings = db.table("overview_display_config").select("""
            user_id, price, volume, rsi, trend, ema, bands, support, resistance, dominance, sentiment, session
        """).execute()

        user_to_settings = separate("user_id", config_response.data)
        strategies = separate("user_id", user_strategies.data, unique=False)
        overview_sections = separate("user_id", overview_sections.data)
        overview_settings = separate("user_id", overview_settings.data)

        strategies_stats = separate("strategy_id", stats_response.data)
        position_stats = separate("strategy_id", position_response.data)
        balance_stats = separate("strategy_id", balance_response.data)
        strategies_configs = separate("strategy_id", strategy_config_response.data)
        history = separate("strategy_id", trade_logs_response.data, unique=False)

        # Update users with fetched data
        for user_id, user_data in self.users.items():
            user_config_row = user_to_settings.get(user_id, {})

            user_data.load(user_config_row, strategies, position_stats,
                           balance_stats, strategies_stats, strategies_configs,
                           history,
                           overview_sections.get(user_id, {}), overview_settings.get(user_id, {}))
