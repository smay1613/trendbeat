from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import LogConfig
from database_helper import DatabaseHelper
from logger_output import log
from state import PositionState, UserBalance, UserStats


class UserSettings:
    def __init__(self):
        self.market_overview_enabled = True
        self.alerts_enabled = True

    def load(self, row):
        for key, value in row.items():
            setattr(self, key, value == 'true')

    def toggle(self, config, enabled):
        if config == "market_overview_enabled":
            self.market_overview_enabled = enabled
        elif config == "alerts_enabled":
            self.alerts_enabled = enabled

    def store(self, user_id):
        data = self.__dict__
        data['user_id'] = user_id

        DatabaseHelper.store("user_config", data)

class UserData:
    def __init__(self):
        self.user_settings = UserSettings()
        self.position_state = PositionState()
        self.balance = UserBalance()
        self.stats = UserStats()

    def load(self, user_config_row, position_state_row, balance_row, stats_row):
        if user_config_row:
            self.user_settings.load(user_config_row)

        if position_state_row:
            self.position_state.load(position_state_row)

        if balance_row:
            self.balance.load(balance_row)

        if stats_row:
            self.stats.load(stats_row)


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
            DatabaseHelper.store("users", {"user_id": user_id, "username": username})
            self.users[user_id] = UserData()


    def load_users(self):
        users = DatabaseHelper.get_table_data("users")
        for user in users:
            self.users[user['user_id']] = UserData()
        self.load_user_data()

    def load_user_data(self):
        def user_to_config(rows):
            user_to_data = {}
            for row in rows:
                user_to_data[row["user_id"]] = row
            return user_to_data

        db = DatabaseHelper.get_client()

        config_response = db.table("user_config").select("user_id, market_overview_enabled, alerts_enabled").execute()
        stats_response = db.table("user_stats").select(
            "user_id, successful_trades, unsuccessful_trades").execute()
        position_response = db.table("position_state").select("""
            user_id, long_position_opened, short_position_opened, 
            long_entry_price, long_entry_size, long_positions,
            short_entry_price, short_entry_size, short_positions, 
            position_qty
        """).execute()
        balance_response = db.table("user_balance").select("""
            user_id, current_capital, allocated_capital, cumulative_profit_loss, total_commission
        """).execute()

        user_to_settings = user_to_config(config_response.data)
        user_to_stat = user_to_config(stats_response.data)
        user_to_position_stat = user_to_config(position_response.data)
        user_to_balance = user_to_config(balance_response.data)

        # Update users with fetched data
        for user_id, user_data in self.users.items():
            user_config_row = user_to_settings.get(user_id)
            position_state_row = user_to_position_stat.get(user_id)
            balance_row = user_to_balance.get(user_id)
            stats_row = user_to_stat.get(user_id)
            user_data.load(user_config_row, position_state_row, balance_row, stats_row)

class BotHandler:
    def __init__(self, user_manager):
        self.user_manager = user_manager

    prompt = "🔒 *Reliable Smart Trading Strategy*\n"
    "📊 *Market Trend-Based*: Powered by precise trend analysis and RSI for accurate decision-making\n"
    "📈 *Precise Indicators*: EMA7, EMA50, RSI — Trusted tools for accurate predictions\n"
    "💼 *Risk-Managed Growth*: Capital protected with strict risk management rules\n"
    "🛡 *Proven Stability*: Minimized drawdowns and adaptive stop-loss for steady returns\n"
    "⚙️ *Real-Time Adjustments*: Automated decisions based on the latest market data\n"
    "📈 *Consistent Performance*: Focused on long-term profitability and market security\n"


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        try:
            self.user_manager.add_user_if_not_exist(user.id, user.username)
            await update.message.reply_text(
                BotHandler.prompt, parse_mode="Markdown"
            )
            await update.message.reply_text(
                f"Hello {user.username}, I am a smart algo trader bot!\n"
                "Here are some commands you can use:\n"
                "/market_overview_on - Enable market overview\n"
                "/market_overview_off - Disable market overview\n"
                "/alerts_on\n"
                "/alerts_off\n"
            )
        except Exception as ex:
            log("Error occured during start: " + str(ex))


    async def toggle_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE, config, enable):
        user_id = update.effective_user.id
        if not self.user_manager.validate(user_id):
            log("Unknown user! Please enter /start first", user_id)
            return

        try:
            settings = self.user_manager.get(user_id).user_settings

            settings.toggle(config, enable)
            settings.store(user_id)

            await update.message.reply_text(f"{config} is set to {enable}.")
        except Exception as ex:
            log("Error occured during market_overview_off: " + str(ex))

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.validate(user_id):
            log("Unknown user! Please enter /start first", user_id)
            return

        try:
            balance = self.user_manager.get(user_id).balance
            await update.message.reply_text(f"{balance.dump()}", parse_mode="Markdown")
        except Exception as ex:
            log("Error occured during balance: " + str(ex))

    async def positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.validate(user_id):
            log("Unknown user! Please enter /start first", user_id)
            return

        try:
            position_state = self.user_manager.get(user_id).position_state
            await update.message.reply_text(f"{position_state.dump()}", parse_mode="Markdown")
        except Exception as ex:
            log("Error occured during balance: " + str(ex))

    async def market_overview_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.toggle_config(update, context, "market_overview_enabled", False)

    async def market_overview_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.toggle_config(update, context, "market_overview_enabled", True)

    async def alerts_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.toggle_config(update, context, "alerts_enabled", False)

    async def alerts_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.toggle_config(update, context, "alerts_enabled", True)


def run_bot_server(user_manager):
    """
    Function to initialize the bot and run it asynchronously.
    """
    # Initialize the bot handler
    bot_handler = BotHandler(user_manager)

    # Create the bot application
    application = Application.builder().token(LogConfig.TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(CommandHandler("help", bot_handler.start))
    application.add_handler(CommandHandler("balance", bot_handler.balance))
    application.add_handler(CommandHandler("positions", bot_handler.positions))
    application.add_handler(CommandHandler("market_overview_on", bot_handler.market_overview_on))
    application.add_handler(CommandHandler("alerts_on", bot_handler.alerts_on))
    application.add_handler(CommandHandler("market_overview_off", bot_handler.market_overview_off))
    application.add_handler(CommandHandler("alerts_off", bot_handler.alerts_off))

    # Run the bot asynchronously
    application.run_polling()