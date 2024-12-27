import copy

from telebot.types import BotCommand
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, filters, MessageHandler, CallbackQueryHandler

from config import LogConfig
from logger_output import log, set_bot_commands_sync
from formatting import format_price


class BotHandler:
    def __init__(self, user_manager, application):
        self.user_manager = user_manager
        self.application = application

    prompt = (
        "ℹ️ *TrendBeat Key Features*\n\n"
        "\n🎢 *Trend-based Trading*\n"
        "- Trades are executed only within strong market trends, ensuring high probability setups.\n"
        "\n🎯 *Momentum Confirmation*\n"
        "- RSI thresholds optimize entry and exit points.\n"
        "\n📊 *Volume Validation*\n"
        "- High-volume conditions validate signals, filtering out noise from low-activity periods.\n"
        "\n🛡️ *Risk Management with ADX*\n"
        "- ADX ensures trading activity occurs only during strong and meaningful trends.\n"
    )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        try:
            self.user_manager.add_user_if_not_exist(user.id, user.username)
            await update.message.reply_text(
                BotHandler.prompt, parse_mode="Markdown"
            )
            await self.show_menu(update, context)

        except Exception as ex:
            log("Error occured during start: " + str(ex))

    async def show_menu(self, update, context):
        main_menu = [
            ["🤖 Strategies"], ["🌎 Market Overview"], ["🛠 Preferences"]
        ]
        context.user_data["current_step"] = "main_menu"
        reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        await update.message.reply_text(f"🏘 Home", parse_mode="Markdown",
                                        reply_markup=reply_markup)


    async def show_preferences(self, update, context):
        preferences = [
            ["🌎 Market Overview", "⚠️ Alerts"],
            ["↩️ Back"]
        ]

        context.user_data["current_step"] = "preferences"
        reply_markup = ReplyKeyboardMarkup(preferences, resize_keyboard=True)
        await update.message.reply_text(f"🔧 Choose setting", parse_mode="Markdown",
                                        reply_markup=reply_markup)

    async def overview_preferences(self, update, context, user_id):
        settings = self.user_manager.get(user_id).user_settings

        overview_enabled = settings.market_overview_enabled
        enabled_icon = "🔔" if overview_enabled else "🔕"
        preferences = [
            [f"{enabled_icon} Notifications"],
            [f"📱 Display settings"],
            ["↩️ Back"]
        ]

        context.user_data["current_step"] = "overview_preferences"
        reply_markup = ReplyKeyboardMarkup(preferences, resize_keyboard=True)
        await update.message.reply_text(f"🛠 Overview settings", parse_mode="Markdown",
                                        reply_markup=reply_markup)

    async def alerts_preferences(self, update, context, user_id):
        settings = self.user_manager.get(user_id).user_settings

        alerts_enabled = settings.alerts_enabled
        enabled_icon = "🔔" if alerts_enabled else "🔕"
        preferences = [
            [f"{enabled_icon} Notifications"],
            ["↩️ Back"]
        ]

        context.user_data["current_step"] = "alerts_preferences"
        reply_markup = ReplyKeyboardMarkup(preferences, resize_keyboard=True)
        await update.message.reply_text(f"🛠 Alerts setting", parse_mode="Markdown",
                                        reply_markup=reply_markup)

    async def overview_preferences_display(self, update, context):
        user_id = update.effective_user.id
        query = update.callback_query
        if query:
            await query.answer()

        settings = self.user_manager.get(user_id).user_settings
        overview_settings_display = settings.overview_settings_display

        if query:
            # Update the displayd section
            section = query.data.replace("display_", "")
            overview_settings_display[section] = not overview_settings_display[section]
            settings.store_overview_settings_display(user_id)

        def state(setting):
            return '💡' if overview_settings_display[setting] else '🌑'

        keyboard = [
            [InlineKeyboardButton(f"💰 Price {state('price')}", callback_data="display_price"),
            InlineKeyboardButton(f"📊 Volume {state('volume')}", callback_data="display_volume"),
            InlineKeyboardButton(f"🟡 RSI {state('rsi')}", callback_data="display_rsi")],
            [InlineKeyboardButton(f"📌 Trend {state('trend')}", callback_data="display_trend"),
            InlineKeyboardButton(f"📊 EMA {state('ema')}", callback_data="display_ema"),
            InlineKeyboardButton(f"📏 Bands {state('bands')}", callback_data="display_bands")],
            [InlineKeyboardButton(f"📉 Support {state('support')}", callback_data="display_support"),
            InlineKeyboardButton(f"📈 Resistance {state('resistance')}", callback_data="display_resistance")],
            [InlineKeyboardButton(f"⚖️ Dominance {state('dominance')}", callback_data="display_dominance"),
            InlineKeyboardButton(f"😎 Sentiment {state('sentiment')}", callback_data="display_sentiment")],
            [InlineKeyboardButton(f"🌐 Session type {state('session')}", callback_data="display_session")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        global overview_printer

        # NOTE: don't use sections!
        overview_text = overview_printer.get_last(None, overview_settings_display)
        if query:
            await query.edit_message_text(f"{overview_text}", parse_mode="Markdown",
                                          reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"{overview_text}", parse_mode="Markdown",
                                            reply_markup=reply_markup)

    async def overview_preferences_notifications_toggle(self, update, context, user_id):
        settings = self.user_manager.get(user_id).user_settings
        context.user_data["current_step"] = "overview_preferences_notifications"
        settings.toggle("market_overview_enabled", not settings.market_overview_enabled)
        settings.store(user_id)

        await update.message.reply_text(f"🌎 Market overview notifications *{'ON' if settings.market_overview_enabled else 'OFF'}*",
                                        parse_mode="Markdown")
        await self.overview_preferences(update, context, user_id)

    async def alerts_preferences_notifications_toggle(self, update, context, user_id):
        settings = self.user_manager.get(user_id).user_settings
        context.user_data["current_step"] = "alerts_preferences_notifications"
        settings.toggle("alerts_enabled", not settings.alerts_enabled)
        settings.store(user_id)

        await update.message.reply_text(f"⚠️ Alerts *{'ON' if settings.alerts_enabled else 'OFF'}*",
                                        parse_mode="Markdown")
        await self.alerts_preferences(update, context, user_id)


    async def handle_user_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.validate(user_id):
            log("Unknown user! Please enter /start first", user_id)
            return

        try:
            user_text = update.message.text
            if not "current_step" in context.user_data:
                await self.show_menu(update, context)
                return

            current_step = context.user_data["current_step"]

            if current_step == "rsi_selection":
                await self.rsi_setup(update, context)
                return

            if user_text.startswith("🎰"):  # strategy
                await self.show_strategy_menu(context, update, user_text)
            elif user_text.startswith("💎 Balance"):
                current_strategy = context.user_data['current_strategy_id']
                current_strategy_name = context.user_data['current_strategy_name']
                user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)
                await update.message.reply_text(f"{current_strategy_name}\n\n"
                                                f"{user_strategy.stats.dump()}", parse_mode="Markdown")
            elif user_text.startswith("🎒 Positions"):
                current_strategy = context.user_data['current_strategy_id']
                current_strategy_name = context.user_data['current_strategy_name']
                user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)
                await update.message.reply_text(f"{current_strategy_name}\n\n"
                                                f"{user_strategy.position_state.dump()}", parse_mode="Markdown")
            elif user_text.startswith("⚙️ Settings"):
                await self.strategy_settings(update, context)
            elif user_text.startswith("🛡️ Risk Management"):
                await self.strategy_settings_risk_management(update, context)
            elif user_text.startswith("📦 Size"):
                await self.strategy_settings_size(update, context)
            elif user_text.startswith("📜 History"):
                await self.dump_position_history(update, context)
            elif user_text.startswith("↩️ Back"):
                if current_step == "strategy_info":
                    await self.strategies(update, context, user_id)
                elif current_step in ["overview_preferences", "alert_preferences"]:
                    await self.show_preferences(update, context)
                elif current_step == "overview_preferences_notifications":
                    await self.overview_preferences(update, context, user_id)
                elif current_step == "alerts_preferences_notifications":
                    await self.alerts_preferences(update, context, user_id)
                elif current_step == "strategy_settings":
                    await self.show_strategy_menu(context, update, context.user_data["current_strategy_name"])
                else:  #elif current_step in ["strategies_overview", "preferences"]:
                    await self.show_menu(update, context)
            elif user_text.startswith(f"🍏 Long RSI"):
                context.user_data['rsi_selection_type'] = "long"
                await self.rsi_setup(update, context)
            elif user_text.startswith(f"🍎 Short RSI"):
                context.user_data['rsi_selection_type'] = "short"
                await self.rsi_setup(update, context)
            elif user_text.startswith("🛠 Preferences"):
                await self.show_preferences(update, context)
            elif user_text.startswith("🌎 Market Overview"):
                if current_step == "main_menu":
                    await self.overview(update, context)
                elif current_step == "preferences":
                    await self.overview_preferences(update, context, user_id)
            elif user_text.startswith("📱 Display settings"):
                await self.overview_preferences_display(update, context)
            elif user_text.startswith("⚠️ Alerts"):
                await self.alerts_preferences(update, context, user_id)
            elif user_text.startswith("🤖 Strategies"):
                await self.strategies(update, context, user_id)
            elif "Notifications" in user_text:
                if current_step == "overview_preferences":
                    await self.overview_preferences_notifications_toggle(update, context, user_id)
                elif current_step == "alerts_preferences":
                    await self.alerts_preferences_notifications_toggle(update, context, user_id)
        except Exception as e:
            log(f"Error during user text: {e}")

    async def dump_position_history(self, update, context):
        user_id = update.effective_user.id
        query = update.callback_query
        if query:
            await query.answer()

        current_strategy = context.user_data['current_strategy_id']
        current_strategy_name = context.user_data['current_strategy_name']
        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)
        strategy_stats = user_strategy.stats

        if query:
            action = query.data.replace("history_", "")
            if action == "back":
                context.user_data['current_history_position'] -= 1
            elif action == "next":
                context.user_data['current_history_position'] += 1
            else:
                return
        else:
            context.user_data['current_history_position'] = 1

        current_history_position = context.user_data['current_history_position']

        step = 5
        current_shown = current_history_position * step
        if current_shown > len(strategy_stats.positions_history):
            current_shown = len(strategy_stats.positions_history)

        keyboard = [
            [InlineKeyboardButton(f"◀️ Back", callback_data="history_back"),
             InlineKeyboardButton(f"{current_shown}/{len(strategy_stats.positions_history)}", callback_data="history_current"),
             InlineKeyboardButton(f"Next ▶️", callback_data="history_next")],
        ]
        if current_shown <= step:
            del keyboard[0][0]
        elif current_shown >= len(strategy_stats.positions_history):
            del keyboard[0][2]

        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.edit_message_text(f"{current_strategy_name}\n\n"
                                            f"{user_strategy.stats.dump_history(current_history_position)}",
                                            parse_mode="Markdown",
                                            reply_markup=reply_markup if len(strategy_stats.positions_history) > step else None)
        else:
            await update.message.reply_text(f"{current_strategy_name}\n\n"
                                            f"{user_strategy.stats.dump_history(current_history_position)}", parse_mode="Markdown",
                                            reply_markup=reply_markup if len(strategy_stats.positions_history) > step else None)

    async def show_strategy_menu(self, context, update, user_text):
        chosen_strategy = user_text
        strategy_names = [strategy_id[0] for strategy_id in context.user_data["strategy_ids"]]
        if chosen_strategy not in strategy_names:
            await update.message.reply_text("Unknown strategy!")
            return

        chosen_strategy_id = [strategy_id[1] for strategy_id in context.user_data["strategy_ids"]
                              if strategy_id[0] == chosen_strategy][-1]
        context.user_data["current_strategy_id"] = chosen_strategy_id
        context.user_data["current_strategy_name"] = chosen_strategy
        context.user_data["current_step"] = "strategy_info"
        settings = [
            ["💎 Balance", "🎒 Positions"],
            ["📜 History", "⚙️ Settings"],
            ["↩️ Back"]
        ]
        reply_markup = ReplyKeyboardMarkup(settings, resize_keyboard=True)
        await update.message.reply_text(f"*{chosen_strategy}* is chosen.", parse_mode="Markdown",
                                        reply_markup=reply_markup)

    async def strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
        try:
            user_data = self.user_manager.get(user_id)
            strategies = user_data.strategies
            strategy_ids = [(f"🎰 {strategy.strategy_config.name}", strategy.strategy_id) for strategy in user_data.strategies.strategies.values()]
            keyboard = [[strategy_id[0]] for strategy_id in strategy_ids]
            keyboard.append(["↩️ Back"])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            context.user_data.clear()
            context.user_data["strategy_ids"] = strategy_ids
            context.user_data["current_step"] = "strategies_overview"
            await update.message.reply_text(f"{strategies.dump()}", parse_mode="Markdown",
                                            reply_markup=reply_markup)
        except Exception as ex:
            log("Error occured during strategies: " + str(ex))

    async def handle_market_overview_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = update.effective_user.id
        if query:
            await query.answer()

        settings = self.user_manager.get(user_id).user_settings
        overview_sections = settings.overview_sections

        if query:
            # Update the toggled section
            section = query.data.replace("toggle_", "")
            overview_sections[section] = not overview_sections[section]
            settings.store_overview_sections(user_id)

        def state(setting):
            return '💡' if overview_sections[setting] else '🌑'

        keyboard = [
            [InlineKeyboardButton(f"💰 Price {state('price')}", callback_data="toggle_price"),
             InlineKeyboardButton(f"📌️ Trend {state('trend')}", callback_data="toggle_trend")],
            [InlineKeyboardButton(f"🛡️ Key Levels {state('support_resistance')}", callback_data="toggle_support_resistance"),
             InlineKeyboardButton(f"⚖ Sentiment {state('sentiment')}", callback_data="toggle_sentiment")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Edit the message to update the keyboard
        global overview_printer
        overview_text = overview_printer.get_last(overview_sections, settings.overview_settings_display)
        if query:
            await query.edit_message_text(f"{overview_text}", parse_mode="Markdown",
                                            reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"{overview_text}", parse_mode="Markdown",
                                            reply_markup=reply_markup if "not collected" not in overview_text else None)

    async def strategy_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["current_step"] = "strategy_settings"
        current_strategy_name = context.user_data['current_strategy_name']

        keyboard = [
            [f"🛡️ Risk Management", "📦 Size"],
            [f"🍏 Long RSI", f"🍎 Short RSI"],
            ['↩️ Back']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(f"⚙️ Select configuration for *{current_strategy_name[2:]}*", parse_mode="Markdown",
                                        reply_markup=reply_markup)

    async def strategy_settings_risk_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = update.effective_user.id
        if query:
            await query.answer()

        current_strategy = context.user_data['current_strategy_id']
        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)

        if not query:
            context.user_data['intermediate_strategy_config'] = copy.deepcopy(user_strategy.strategy_config)

        settings = context.user_data['intermediate_strategy_config']
        hide_keyboard = False
        if query:
            # Update the toggled section
            section = query.data.replace("strategy_settings_risk_management_", "")
            if section == "reset":
                context.user_data['intermediate_strategy_config'] = copy.deepcopy(user_strategy.strategy_config)
                settings = context.user_data['intermediate_strategy_config']
            elif section == "save":
                user_strategy.strategy_config = copy.deepcopy(settings)
                user_strategy.strategy_config.store(current_strategy)
                hide_keyboard = True
            elif section == "momentum":
                if settings.min_adx > 0:
                    settings.min_adx = 0
                else:
                    settings.min_adx = 15
            elif section == "strong_trend":
                settings.allow_weak_trend = not settings.allow_weak_trend
            elif section == "reversal_stop":
                settings.close_on_trend_reverse = not settings.close_on_trend_reverse
            elif section == "high_vol":
                settings.high_volume_only = not settings.high_volume_only
                
        def state(setting):
            return '✅' if setting else '❌'

        keyboard = [
            [InlineKeyboardButton(f"🌀 Strong Momentum {state(settings.min_adx >= 15)}", callback_data="strategy_settings_risk_management_momentum"),
            InlineKeyboardButton(f"💹️ Strong Trend {state(not settings.allow_weak_trend)}", callback_data="strategy_settings_risk_management_strong_trend")],
            [InlineKeyboardButton(f"🔄 Reversal Stop {state(settings.close_on_trend_reverse)}", callback_data="strategy_settings_risk_management_reversal_stop"),
            InlineKeyboardButton(f"📊 High Vol. {state(settings.high_volume_only)}", callback_data="strategy_settings_risk_management_high_vol")],
            [InlineKeyboardButton(f"♻️ Reset", callback_data="strategy_settings_risk_management_reset"),
             InlineKeyboardButton(f"💾 Save", callback_data="strategy_settings_risk_management_save")]
        ]
        
        state_only_msg = (f"*{context.user_data['current_strategy_name']}*\n"
                          f"🛡 *Risk Management* settings saved 💾\n\n"
         f"🌀 *Strong Momentum* {state(settings.min_adx >= 15)}\n"
         f"💹️ *Strong Trend* {state(not settings.allow_weak_trend)}\n"
         f"🔄 *Reversal Stop* {state(settings.close_on_trend_reverse)}\n"
         f"📊 *High Vol.* {state(settings.high_volume_only)}\n"
         )
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        help_message = (
            f"🌀 *Strong Momentum* {state(settings.min_adx >= 15)}\n"
            "  ▫ *ADX >= 15*:   \n    The ADX measures the strength of the trend. When ADX is above 15, the market is in a strong trend, indicating a higher probability of trend continuation.\n"
            f"\n💹️ *Strong Trend* {state(not settings.allow_weak_trend)}\n"
            '  ▫ *EMA 7 < EMA 25*: \n    When the short-term moving average (EMA 7) is below the medium-term moving average (EMA 25), it signals a downtrend (_SHORT_).\n'
            '  ▫ *EMA 7 > EMA 25*: \n    If EMA 7 is above EMA 25, this signals an uptrend (_LONG_).\n'
            '  ▫ *EMA 7 vs EMA 50*: \n    If EMA 7 is above/below EMA 25 but not EMA 50, the trend is considered _weak_. '
            'A _strong_ trend occurs when both EMA 25 and EMA 50 are crossed in the same direction.\n'
            f"\n🔄 *Reversal Stop* {state(settings.close_on_trend_reverse)}\n"
            "  ▫ *Trend Direction Change*: \n    If the trend changes direction (e.g., from a strong uptrend to a strong downtrend), close the position to avoid potential losses.\n"
            f"\n📊 *High Vol.* {state(settings.high_volume_only)}\n"
            "  ▫ *Volume greater than the 50-period average*: \n    An increase in volume beyond the 50-period average signals heightened market activity, which could indicate either a continuation of the trend or a potential reversal.\n"
        )

        if query:
            await query.edit_message_text(f"{help_message if not hide_keyboard else state_only_msg}", parse_mode="Markdown",
                                          reply_markup=reply_markup if not hide_keyboard else None)
        else:
            await update.message.reply_text(f"{help_message}", parse_mode="Markdown",
                                            reply_markup=reply_markup)

    async def strategy_settings_size(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = update.effective_user.id
        if query:
            await query.answer()

        current_strategy = context.user_data['current_strategy_id']
        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)
        strategy_config = user_strategy.strategy_config

        hide_keyboard = False
        if not query:
            context.user_data['intermediate_position_size'] = user_strategy.strategy_config.position_size
            context.user_data['intermediate_position_leverage'] = user_strategy.strategy_config.leverage
        else:
            # Update the toggled section

            section = query.data.replace("strategy_settings_", "")
            if "save" in section:
                user_strategy.strategy_config.position_size = context.user_data['intermediate_position_size']
                user_strategy.strategy_config.leverage = context.user_data['intermediate_position_leverage']
                user_strategy.strategy_config.store(current_strategy)
                hide_keyboard = True
            elif "size" in section:
                section = section.replace("position_size_", "")
                context.user_data['intermediate_position_size'] = int(section)
            elif "leverage" in section:
                section = section.replace("position_leverage_", "")
                context.user_data['intermediate_position_leverage'] = int(section)

        current_size = context.user_data['intermediate_position_size']
        current_leverage = context.user_data['intermediate_position_leverage']

        def tick_mark(value, is_leverage):
            if is_leverage:
                return ' ☑️' if value == current_leverage else ''

            return ' ☑️' if value == current_size else ''

        keyboard = [
            [InlineKeyboardButton(f"50${tick_mark(50, False)}", callback_data="strategy_settings_position_size_50"),
             InlineKeyboardButton(f"100${tick_mark(100, False)}", callback_data="strategy_settings_position_size_100"),
             InlineKeyboardButton(f"150${tick_mark(150, False)}", callback_data="strategy_settings_position_size_150"),
             InlineKeyboardButton(f"200${tick_mark(200, False)} ⚠️", callback_data="strategy_settings_position_size_200")],
            [InlineKeyboardButton(f"x5{tick_mark(5, True)}", callback_data="strategy_settings_position_leverage_5"),
             InlineKeyboardButton(f"x10{tick_mark(10, True)}", callback_data="strategy_settings_position_leverage_10"),
             InlineKeyboardButton(f"x15{tick_mark(15, True)}", callback_data="strategy_settings_position_leverage_15"),
             InlineKeyboardButton(f"x20{tick_mark(20, True)} ⚠️", callback_data="strategy_settings_position_leverage_20")],
            [InlineKeyboardButton(f"💾 Save", callback_data="strategy_settings_position_save")]
        ]

        message = (
            f"📦 *Position size settings*: `{format_price(strategy_config.position_size)} x{strategy_config.leverage}`\n\n"
            "Select your *Position Size* and *Leverage*:\n\n"
            "- *Position Size*: The amount you want to invest per trade (e.g., 150$).\n"
            "- *Leverage*: Multiplies your trading power. For example, with x10 leverage, you control 10 times the amount of your capital.\n\n"
            "⚠️ *Warnings*:\n"
            "- *Higher leverage = Higher risk*. While leverage amplifies profits, it also increases potential losses.\n"
            "- High leverage makes your position more *vulnerable to liquidation*. Be cautious with larger leverage.\n\n"
            "👇 *Choose below* to set your preferences:"
        )

        current_strategy_name = context.user_data['current_strategy_name']

        short_msg = (f"{current_strategy_name}\n"
                     f"📦 💾 *Position size*: `{format_price(strategy_config.position_size)} x{strategy_config.leverage}`\n\n")

        reply_markup = InlineKeyboardMarkup(keyboard)

        if query:
            await query.edit_message_text(f"{message if not hide_keyboard else short_msg}", parse_mode="Markdown",
                                          reply_markup=reply_markup if not hide_keyboard else None)
        else:
            await update.message.reply_text(f"{message}", parse_mode="Markdown",
                                            reply_markup=reply_markup)

    async def rsi_setup(self, update, context):
        user_id = update.effective_user.id
        current_strategy = context.user_data['current_strategy_id']
        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)
        strategy_config = user_strategy.strategy_config

        rsi_type = context.user_data['rsi_selection_type']
        is_new_dialog = False
        if context.user_data['current_step'] != "rsi_selection":
            context.user_data['current_step'] = "rsi_selection"
            current_rsi_params = {
                "enter": strategy_config.long_buy_rsi_enter if rsi_type == "long" else strategy_config.short_sell_rsi_enter,
                "dca": strategy_config.long_buy_additional_enter if rsi_type == "long" else strategy_config.short_sell_additional_enter,
                "exit": strategy_config.long_buy_rsi_exit if rsi_type == "long" else strategy_config.short_sell_rsi_exit
            }
            context.user_data['intermediate_rsi_selection'] = copy.deepcopy(current_rsi_params)
            is_new_dialog = True

        validation_fail = False
        finished = False
        intermediate_rsi = context.user_data['intermediate_rsi_selection']

        if not is_new_dialog:
            user_text = update.message.text
            current_selection_step = context.user_data['rsi_selection_step']
            if user_text == '↩️ Back':
                if current_selection_step == "enter":
                    await self.strategy_settings(update, context)
                    return
                elif current_selection_step == "dca":
                    context.user_data['rsi_selection_step'] = "enter"
                elif current_selection_step == "exit":
                    context.user_data['rsi_selection_step'] = "dca"
            elif not user_text.isdigit() or not (1 <= int(user_text) <= 99):
                validation_fail = True
            else:
                intermediate_rsi[current_selection_step] = user_text
                if current_selection_step == "enter":
                    context.user_data['rsi_selection_step'] = "dca"
                elif current_selection_step == "dca":
                    context.user_data['rsi_selection_step'] = "exit"
                else:
                    finished = True
        else:
            context.user_data['rsi_selection_step'] = "enter"

        current_selection_step = context.user_data['rsi_selection_step']

        keyboard = [
            [f"{intermediate_rsi[current_selection_step]}"],
            ['↩️ Back']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        text = ""
        if not validation_fail and not finished:
            if current_selection_step == "enter":
                text = ('📍 Select *entry* RSI\n'
                        f'_Type new or select_ 👇')
            elif current_selection_step == "dca":
                text = ('🔄 Select *DCA* RSI\n'
                        f'📍 `{intermediate_rsi["enter"]}` → 🔄\n'
                        f'_Type new or select_ 👇')
            else:
                text = ('🏁 Select *exit* RSI\n'
                        f'📍 `{intermediate_rsi["enter"]}` → `{intermediate_rsi["dca"]}` 🔄 → 🏁\n'
                        f'_Type new or select_ 👇\n')
        elif finished:
            is_short = context.user_data['rsi_selection_type'] == 'short'
            old_config = strategy_config.dump(risks=False, long_rsi=not is_short, short_rsi=is_short, pos_size=False)

            if is_short:
                strategy_config.setup_short_position(intermediate_rsi['enter'], intermediate_rsi['dca'], intermediate_rsi['exit'])
            else:
                strategy_config.setup_long_position(intermediate_rsi['enter'], intermediate_rsi['dca'], intermediate_rsi['exit'])

            strategy_config.store(current_strategy)

            new_config = strategy_config.dump(risks=False, long_rsi=not is_short, short_rsi=is_short, pos_size=False)
            text = (f"{'🍎 Short RSI' if is_short else '🍏 Long RSI'} saved 💾\n"
                    f"_Was:_\n"
                    f"{old_config.splitlines()[1]}\n"
                    f"*New:*\n"
                    f"{new_config.splitlines()[1]}\n")
            await update.message.reply_text(f"{text}", parse_mode="Markdown",
                                            reply_markup=reply_markup)

            await self.strategy_settings(update, context)
            return
        elif validation_fail:
            text = "❌ Please enter a valid number in range 1-99"

        await update.message.reply_text(f"{text}", parse_mode="Markdown",
                                        reply_markup=reply_markup)

    async def overview(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self.handle_market_overview_toggle(update, context)
        except Exception as ex:
            log("Error occured during overview: " + str(ex))





def run_bot_server(user_manager):
    """
    Function to initialize the bot and run it asynchronously.
    """
    # Initialize the bot handler

    # Create the bot application
    application = Application.builder().token(LogConfig.TELEGRAM_TOKEN).build()
    bot_handler = BotHandler(user_manager, application)

    # Add command handlers
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(CommandHandler("help", bot_handler.start))
    # application.add_handler(CommandHandler("strategies", bot_handler.strategies))
    # application.add_handler(CommandHandler("overview", bot_handler.overview))
    # application.add_handler(CommandHandler("market_overview_on", bot_handler.market_overview_on))
    # application.add_handler(CommandHandler("alerts_on", bot_handler.alerts_on))
    # application.add_handler(CommandHandler("market_overview_off", bot_handler.market_overview_off))
    # application.add_handler(CommandHandler("alerts_off", bot_handler.alerts_off))
    application.add_handler(MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=bot_handler.handle_user_response))

    application.add_handler(CallbackQueryHandler(bot_handler.handle_market_overview_toggle, pattern="toggle"))
    application.add_handler(CallbackQueryHandler(bot_handler.overview_preferences_display, pattern="display"))
    application.add_handler(CallbackQueryHandler(bot_handler.strategy_settings_risk_management, pattern="strategy_settings_risk_management"))
    application.add_handler(CallbackQueryHandler(bot_handler.strategy_settings_size, pattern="strategy_settings_position_"))
    application.add_handler(CallbackQueryHandler(bot_handler.dump_position_history, pattern="history"))

    set_bot_commands_sync()

    # loop.close()
    application.run_polling()

