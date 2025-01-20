import asyncio
import copy
import traceback

from telebot.types import BotCommand
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, filters, MessageHandler, CallbackQueryHandler

from config import LogConfig
from logger_output import log, set_bot_commands_sync, log_error
from formatting import format_price
import market_overview


def safe_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            await func(*args, **kwargs)
        except Exception as e:
            log_error(f"Error in handler {func.__name__}: {e}\n"
                      f"{traceback.format_exc()}")

    return wrapper

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


    @safe_handler
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.user_manager.add_user_if_not_exist(user.id, user.username)
        await update.message.reply_text(
            BotHandler.prompt, parse_mode="Markdown"
        )
        await self.show_menu(update, context)


    def cleanup_current_state(self, user_data, full=True):
        clean_list = ['selection_message_id', 'active_rsi_selection', 'rsi_selection_step',
                      'active_rsi_selection_strategy', 'active_rsi_selection_strategy_name']
        if full:
            clean_list += ['intermediate_rsi_selection', 'intermediate_rsi_config',
                           'last_rsi_status_message', 'rsi_selection_type']
        # rsi:
        for key in clean_list:
            if key in user_data:
                del user_data[key]

    @safe_handler
    async def show_menu(self, update, context):
        main_menu = [
            ["🤖 Strategies"], ["🌎 Market Overview"]
        ]

        reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        await update.message.reply_text(f"🏘 Home", parse_mode="Markdown",
                                        reply_markup=reply_markup)

    @safe_handler
    async def handle_user_response(self, update, context):
        user_id = update.effective_user.id
        if not self.user_manager.validate(user_id):
            log("Unknown user! Please enter /start first", user_id)
            return

        user_text = update.message.text

        if user_text.startswith("🎰"):  # strategy
            await self.show_strategy_menu(update, context, user_text)
        elif user_text.startswith("🏘 Home"):
                await self.show_menu(update, context)
        elif user_text.startswith("🌎 Market Overview"):
            await self.overview(update, context)
        elif user_text.startswith("🤖 Strategies"):
            await self.strategies(update, context, user_id)
        elif 'active_rsi_selection' in context.user_data:
            await self.rsi_setup_enter_number(update, context,
                                              context.user_data['active_rsi_selection_strategy'],
                                              context.user_data['active_rsi_selection_strategy_name'])

    @safe_handler
    async def dump_position_history(self, update, context, user_strategy=None):
        user_id = update.effective_user.id
        query = update.callback_query if not user_strategy else None
        if query:
            await query.answer()

        if not user_strategy:
            message_text = query.message.text if query else update.message.text
        else:
            message_text = update.callback_query.message.text
        current_strategy, current_strategy_name = self.determine_current_strategy(message_text, context.user_data)
        if not user_strategy:
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
            last_position = int(current_shown / step)
            context.user_data['current_history_position'] = last_position + 1

        keyboard = [
            [InlineKeyboardButton(f"◀️ Previous", callback_data="history_back"),
             InlineKeyboardButton(f"{current_shown}/{len(strategy_stats.positions_history)}", callback_data="history_current"),
             InlineKeyboardButton(f"Next ▶️", callback_data="history_next")],
            [InlineKeyboardButton('↩️ Back', callback_data="discard_message")]
        ]
        discard_markup = InlineKeyboardMarkup([[InlineKeyboardButton('↩️ Back', callback_data="discard_message")]])

        if current_shown <= step:
            del keyboard[0][0]
        elif current_shown >= len(strategy_stats.positions_history):
            del keyboard[0][2]

        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.edit_message_text(f"{current_strategy_name}\n\n"
                                            f"{user_strategy.stats.dump_history(current_history_position)}",
                                            parse_mode="Markdown",
                                            reply_markup=reply_markup if len(strategy_stats.positions_history) > step else discard_markup)
        else:
            message = update.message if update.message else update.callback_query.message # can be called from inline button
            await message.reply_text(f"{current_strategy_name}\n\n"
                                    f"{user_strategy.stats.dump_history(current_history_position)}", parse_mode="Markdown",
                                    reply_markup=reply_markup if len(strategy_stats.positions_history) > step else discard_markup)

    @safe_handler
    async def discard_message(self, update, context):
        await update.callback_query.delete_message()

    def determine_current_strategy(self, message, user_data):
        chosen_strategy = message.splitlines()[0]
        strategy_ids = user_data["strategy_ids"]

        strategy_names = [strategy_id[0] for strategy_id in strategy_ids]
        if chosen_strategy not in strategy_names:
            log_error(f"Can't determine strategy in message {message}")
            return

        chosen_strategy_id = [strategy_id[1] for strategy_id in strategy_ids
                              if strategy_id[0] == chosen_strategy][-1]

        return chosen_strategy_id, chosen_strategy

    @safe_handler
    async def show_strategy_menu(self, update, context, user_text=None):
        user_id = update.effective_user.id

        query = update.callback_query if not user_text else None
        if query:
            await query.answer()

        if user_text:
            current_strategy, current_strategy_name = self.determine_current_strategy(user_text, context.user_data)
        else:
            message_text = query.message.text if query else update.message.text
            current_strategy, current_strategy_name = self.determine_current_strategy(message_text, context.user_data)

        section = query.data.replace("strategy_menu_", "") if query else None

        inline_keyboard = [
            [InlineKeyboardButton("💎 Balance", callback_data="strategy_menu_balance"),
             InlineKeyboardButton("🎒 Positions", callback_data="strategy_menu_positions")],
            [InlineKeyboardButton("📜 History", callback_data="strategy_menu_history"),
             InlineKeyboardButton("⚙️ Settings", callback_data="strategy_menu_settings")],
            [InlineKeyboardButton('↩️ Back', callback_data="discard_message"),
             InlineKeyboardButton('🔄 Refresh', callback_data="strategy_menu_refresh")]
        ]
        inline_markup = InlineKeyboardMarkup(inline_keyboard)

        user_data = self.user_manager.get(user_id)
        chosen_strategy_object = user_data.strategies.get_strategy(current_strategy)
        if not query or section == "refresh":
            risks_enabled = context.user_data.get('strategies_view_expanded', False)
            rsi_enabled = context.user_data.get('strategies_view_expanded', False)

            if not user_text:
                message = update.message if not query else query.message
            else:
                message = update.callback_query.message
            new_text = user_data.strategies.dump_strategy(chosen_strategy_object, risks_enabled, rsi_enabled, False)
            if section == "refresh":
                if query.message.text_markdown.strip() != new_text.strip():
                    await message.edit_text(f"{new_text}", parse_mode="Markdown", reply_markup=inline_markup)
            else:
                await message.reply_text(f"{new_text}", parse_mode="Markdown", reply_markup=inline_markup)
        else:

            keyboard = [
                [InlineKeyboardButton('↩️ Back', callback_data="discard_message")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if section == "balance":
                await query.message.reply_text(f"{current_strategy_name}\n\n"
                                                f"{chosen_strategy_object.stats.dump()}", parse_mode="Markdown",
                                               reply_markup=reply_markup)
            elif section == "positions":
                await query.message.reply_text(f"{current_strategy_name}\n\n"
                                                f"{chosen_strategy_object.position_state.dump()}", parse_mode="Markdown",
                                               reply_markup=reply_markup)
            elif section == "history":
                await self.dump_position_history(update, context, chosen_strategy_object)
            elif section == "settings":
                await self.strategy_settings(update, context)

    @safe_handler
    async def strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
        if update:
            query = update.callback_query
            user_id = update.effective_user.id
        else:
            query = None

        if query:
            await query.answer()

        user_data = self.user_manager.get(user_id)
        strategies = user_data.strategies

        if not 'strategies_view_expanded' in context.user_data:
            context.user_data['strategies_view_expanded'] = False

        is_expanded = context.user_data["strategies_view_expanded"]
        if query:
            # Update the toggled section
            section = query.data.replace("strategies_menu_", "")
            if section.startswith("select_"):
                strategy = section.replace("select_", "")
                await self.show_strategy_menu(update, context, strategy)
                return
            elif section.startswith("view_"):
                context.user_data['strategies_view_expanded'] = not context.user_data["strategies_view_expanded"]

        is_expanded = context.user_data["strategies_view_expanded"]

        inline_keyboard = [
            [InlineKeyboardButton(f'{"➕" if not is_expanded else "➖"} Show {"more" if not is_expanded else "less"}',
                                  callback_data='strategies_menu_view_more'),
            InlineKeyboardButton(f"🔄 Refresh", callback_data="strategies_menu_refresh")]
        ]

        strategy_ids = [(f"🎰 {strategy.strategy_config.name}", strategy.strategy_id) for strategy in
                        user_data.strategies.strategies.values()]
        strategy_keyboard = [
            [InlineKeyboardButton(strategy_id[0], callback_data=f"strategies_menu_select_{strategy_id[0]}")]
            for strategy_id in strategy_ids]
        for row in reversed(strategy_keyboard):
            inline_keyboard.insert(0, row)
        context.user_data["strategy_ids"] = strategy_ids

        inline_markup = InlineKeyboardMarkup(inline_keyboard)

        risks_enabled = context.user_data['strategies_view_expanded']
        rsi_enabled = context.user_data['strategies_view_expanded']

        if not query:
            await update.message.reply_text(f"{strategies.dump(risks_enabled, rsi_enabled)}", parse_mode="Markdown",
                                            reply_markup=inline_markup)
        else:  # refresh
            new_text = strategies.dump(risks_enabled, rsi_enabled)
            if query.message.text_markdown.strip() != new_text.strip():
                await query.edit_message_text(f"{new_text}", parse_mode="Markdown",
                                                reply_markup=inline_markup)

    @safe_handler
    async def handle_market_overview_toggle(self, update, context):
        query = update.callback_query
        user_id = update.effective_user.id

        if query:
            await query.answer()

        settings = self.user_manager.get(user_id).user_settings
        overview_sections = settings.overview_sections

        overviews_count = len(market_overview.overview_printer.last_market_overviews)

        if query:
            # Update the toggled section
            if query.data.startswith("toggle_"):
                section = query.data.replace("toggle_", "")
                if section == "sections_view":
                    context.user_data['market_overview_sections_view_enabled'] = not context.user_data['market_overview_sections_view_enabled']
                elif section == "more_sections_view":
                    context.user_data['market_overview_more_sections_view_enabled'] = not context.user_data['market_overview_more_sections_view_enabled']
                elif section == "alerts":
                    settings.toggle("alerts_enabled", not settings.alerts_enabled)
                    settings.store(user_id)
                elif section == "back":
                    context.user_data['current_overview_position'] -= 1
                elif section == "next":
                    context.user_data['current_overview_position'] += 1
                elif section != "refresh":
                    overview_sections[section] = not overview_sections[section]
                    settings.store_overview_sections(user_id)
            elif query.data.startswith("more_"):
                more_section = query.data.replace("more_", "")
                context.user_data['market_overview_more_section'] = more_section
                context.user_data['market_overview_more_sections_view_enabled'] = True
            elif query.data.startswith("display_"):
                section = query.data.replace("display_", "")
                overview_settings_display = settings.overview_settings_display
                overview_settings_display[section] = not overview_settings_display[section]
                settings.store_overview_settings_display(user_id)
        else:
            context.user_data['current_overview_position'] = overviews_count
            context.user_data['market_overview_sections_view_enabled'] = False
            context.user_data['market_overview_more_section'] = None
            context.user_data['market_overview_more_sections_view_enabled'] = False

        def state(setting):
            return '💡' if overview_sections[setting] else '🌑'

        current_shown = context.user_data['current_overview_position']

        navigation_keyboard = [InlineKeyboardButton(f"◀️ ", callback_data="toggle_back"),
                             InlineKeyboardButton(f"{current_shown}/{overviews_count}", callback_data="none"),
                             InlineKeyboardButton(f" ▶️", callback_data="toggle_next")]

        if current_shown >= overviews_count:
            del navigation_keyboard[2]
        if current_shown <= 1:
            del navigation_keyboard[0]

        keyboard = []
        display_view = context.user_data['market_overview_sections_view_enabled']
        display_more_view = context.user_data[
            'market_overview_more_sections_view_enabled'] if 'market_overview_more_sections_view_enabled' in context.user_data else False
        more_section = context.user_data[
            'market_overview_more_section'] if 'market_overview_more_section' in context.user_data else None

        if not display_view:
            keyboard.append(navigation_keyboard)
            keyboard.append([InlineKeyboardButton(f"⚙️ Settings", callback_data="toggle_sections_view"),
                             InlineKeyboardButton(f"🖼 Chart", callback_data="toggle_chart_open",
                                                  url="https://www.tradingview.com/chart/ddsB3Vf5/")])
            service_keyboard = [InlineKeyboardButton('↩️ Back', callback_data="discard_message"),
                                InlineKeyboardButton('🔄 Refresh', callback_data='toggle_refresh')]

            keyboard.append(service_keyboard)
        elif display_more_view:
            overview_settings_display = settings.overview_settings_display
            def display_state(setting):
                return '💡' if overview_settings_display[setting] else '🌑'

            more_sections_keyboard = {
                "price": [InlineKeyboardButton(f"💰 Price {display_state('price')}", callback_data="display_price"),
                          InlineKeyboardButton(f"📊 Volume {display_state('volume')}", callback_data="display_volume"),
                          InlineKeyboardButton(f"🟡 RSI {display_state('rsi')}", callback_data="display_rsi")],
                "trend": [InlineKeyboardButton(f"📌 Trend {display_state('trend')}", callback_data="display_trend"),
                          InlineKeyboardButton(f"📊 EMA {display_state('ema')}", callback_data="display_ema"),
                          InlineKeyboardButton(f"📏 Bands {display_state('bands')}", callback_data="display_bands")],
                "support/Resistance": [InlineKeyboardButton(f"📉 Support {display_state('support')}", callback_data="display_support"),
                                       InlineKeyboardButton(f"📈 Resistance {display_state('resistance')}", callback_data="display_resistance")],
                "sentiment": [InlineKeyboardButton(f"⚖️ Dominance {display_state('dominance')}", callback_data="display_dominance"),
                              InlineKeyboardButton(f"😎 Sentiment {display_state('sentiment')}", callback_data="display_sentiment")],
            }

            current_section = more_sections_keyboard[more_section]
            for row in current_section:
                keyboard.append([row])
            keyboard.append(
                [InlineKeyboardButton(f"↩️ Back",
                                      callback_data="toggle_more_sections_view")])
        else:
            alerts_enabled = settings.alerts_enabled
            enabled_icon = "🔔" if alerts_enabled else "🔕"
            display_keyboard = [
                [InlineKeyboardButton(f"⚠️ Alerts {enabled_icon}", callback_data="toggle_alerts")],
                [InlineKeyboardButton(f"💰 Price {state('price')}", callback_data="toggle_price"), InlineKeyboardButton("➤", callback_data="more_price")],
                [InlineKeyboardButton(f"📌️ Trend {state('trend')}", callback_data="toggle_trend"), InlineKeyboardButton("➤", callback_data="more_trend")],
                [InlineKeyboardButton(f"🛡️ Key Levels {state('support_resistance')}", callback_data="toggle_support/Resistance"), InlineKeyboardButton("➤", callback_data="more_support/Resistance")],
                [InlineKeyboardButton(f"⚖ Sentiment {state('sentiment')}", callback_data="toggle_sentiment"), InlineKeyboardButton("➤", callback_data="more_sentiment")],
                [InlineKeyboardButton(f"↩️ Back", callback_data="toggle_sections_view")]
            ]
            for keyboard_line in display_keyboard:
                keyboard.append(keyboard_line)

        reply_markup = InlineKeyboardMarkup(keyboard)

        overview_text = market_overview.overview_printer.get_last(overview_sections, settings.overview_settings_display, index=current_shown - 1)

        if query:
            is_changed = not (query.data == "toggle_refresh" and query.message.text_markdown.strip() == overview_text.strip())
            if is_changed:
                await query.edit_message_text(f"{overview_text}", parse_mode="Markdown",
                                              reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"{overview_text}", parse_mode="Markdown",
                                            reply_markup=reply_markup if "not collected" not in overview_text else None)

    @safe_handler
    async def strategy_settings(self, update, context):
        query = update.callback_query
        if query:
            await query.answer()
        message_text = update.message.text if not query else query.message.text
        current_strategy, current_strategy_name = self.determine_current_strategy(message_text, context.user_data)

        user_id = update.effective_user.id

        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)

        keyboard = [
            [InlineKeyboardButton(f"🛡️ Risk Management", callback_data="setup_strategy_settings_risk_management"),
             InlineKeyboardButton("📦 Size", callback_data="setup_strategy_settings_size")],
            [InlineKeyboardButton(f"🍏 Long RSI", callback_data="setup_strategy_settings_long_rsi"),
             InlineKeyboardButton(f"🍎 Short RSI", callback_data="setup_strategy_settings_short_rsi")],
            [InlineKeyboardButton('↩️ Back', callback_data="discard_message"),
             InlineKeyboardButton('🔄 Refresh', callback_data="current_strategy_settings_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = update.message if update.message else query.message

        new_text = (f"{current_strategy_name}\n\n"
                    f"{user_strategy.strategy_config.dump(risks=True, long_rsi=True, short_rsi=True)}")
        if not query:
            await message.reply_text(new_text,
                                     parse_mode="Markdown", reply_markup=reply_markup)
        elif query.message.text_markdown.strip() != new_text.strip():
            await query.edit_message_text(new_text,
                                          parse_mode="Markdown", reply_markup=reply_markup)

    @safe_handler
    async def setup_strategy_settings(self, update, context):
        query = update.callback_query
        await query.answer()
        section = query.data.replace("setup_strategy_settings_", "")

        if section == "risk_management":
            await self.strategy_settings_risk_management(update, context, intro=True)
        elif section == "size":
            await self.strategy_settings_size(update, context, intro=True)
        elif section == "long_rsi":
            await self.rsi_setup_show(update, context, rsi_type="long")
        elif section == "short_rsi":
            await self.rsi_setup_show(update, context, rsi_type="short")

    @safe_handler
    async def strategy_settings_risk_management(self, update, context, intro=False):
        query = update.callback_query
        user_id = update.effective_user.id

        if not intro:
            await query.answer()

        message_text = query.message.text if query else update.message.text
        current_strategy, current_strategy_name = self.determine_current_strategy(message_text, context.user_data)

        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)

        if intro:
            context.user_data['intermediate_strategy_config'] = copy.deepcopy(user_strategy.strategy_config)

        settings = context.user_data['intermediate_strategy_config']
        hide_keyboard = False

        # Update the toggled section
        if not intro:
            section = query.data.replace("strategy_settings_risk_management_", "")
            if section == "save":
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
            [InlineKeyboardButton('↩️ Back', callback_data="discard_message"),
             # InlineKeyboardButton(f"♻️ Reset", callback_data="strategy_settings_risk_management_reset"),
             InlineKeyboardButton(f"💾 Save", callback_data="strategy_settings_risk_management_save")]
        ]
        
        state_only_msg = (f"{current_strategy_name}\n\n"
                          f"🛡 *Risk Management* settings saved 💾\n\n"
         f"🌀 *Strong Momentum* {state(settings.min_adx >= 15)}\n"
         f"💹️ *Strong Trend* {state(not settings.allow_weak_trend)}\n"
         f"🔄 *Reversal Stop* {state(settings.close_on_trend_reverse)}\n"
         f"📊 *High Vol.* {state(settings.high_volume_only)}\n"
         )
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        help_message = (
            f"{current_strategy_name}\n\n"
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

        if not intro:
            discard_markup = InlineKeyboardMarkup([[InlineKeyboardButton('↩️ Back', callback_data="discard_message")]])
            await query.edit_message_text(f"{help_message if not hide_keyboard else state_only_msg}", parse_mode="Markdown",
                                          reply_markup=reply_markup if not hide_keyboard else discard_markup)
        else:
            await query.message.reply_text(f"{help_message}", parse_mode="Markdown",
                                            reply_markup=reply_markup)

    @safe_handler
    async def strategy_settings_size(self, update, context, intro=False):
        query = update.callback_query
        user_id = update.effective_user.id
        if not intro:
            await query.answer()

        # current_strategy = context.user_data['current_strategy_id']
        message_text = query.message.text if query else update.message.text
        current_strategy, current_strategy_name = self.determine_current_strategy(message_text, context.user_data)

        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)
        strategy_config = user_strategy.strategy_config

        hide_keyboard = False
        if intro:
            context.user_data['intermediate_position_size'] = user_strategy.strategy_config.position_size
            context.user_data['intermediate_position_leverage'] = user_strategy.strategy_config.leverage
        else:
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
            [InlineKeyboardButton('↩️ Back', callback_data="discard_message"),
             InlineKeyboardButton(f"💾 Save", callback_data="strategy_settings_position_save")]
        ]

        message = (
            f"{current_strategy_name}\n\n"
            f"📦 *Position size settings*: `{format_price(strategy_config.position_size)} x{strategy_config.leverage}`\n\n"
            "Select your *Position Size* and *Leverage*:\n\n"
            "- *Position Size*: The amount you want to invest per trade (e.g., 150$).\n"
            "- *Leverage*: Multiplies your trading power. For example, with x10 leverage, you control 10 times the amount of your capital.\n\n"
            "⚠️ *Warnings*:\n"
            "- *Higher leverage = Higher risk*. While leverage amplifies profits, it also increases potential losses.\n"
            "- High leverage makes your position more *vulnerable to liquidation*. Be cautious with larger leverage.\n\n"
            "👇 *Choose below* to set your preferences:"
        )

        # current_strategy_name = context.user_data['current_strategy_name']

        short_msg = (f"{current_strategy_name}\n"
                     f"📦 💾 *Position size*: `{format_price(strategy_config.position_size)} x{strategy_config.leverage}`\n\n")

        reply_markup = InlineKeyboardMarkup(keyboard)

        if not intro:
            discard_markup = InlineKeyboardMarkup([[InlineKeyboardButton('↩️ Back', callback_data="discard_message")]])
            await query.edit_message_text(f"{message if not hide_keyboard else short_msg}", parse_mode="Markdown",
                                          reply_markup=reply_markup if not hide_keyboard else discard_markup)
        else:
            await query.message.reply_text(f"{message}", parse_mode="Markdown",
                                            reply_markup=reply_markup)

    @safe_handler
    async def rsi_setup_show(self, update, context, rsi_type):
        user_id = update.effective_user.id

        message = update.callback_query.message
        message_text = message.text
        current_strategy, current_strategy_name = self.determine_current_strategy(message_text, context.user_data)

        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)
        strategy_config = user_strategy.strategy_config

        await self.delete_last_rsi_selection_message(context, update)
        await self.remove_last_rsi_status_message(context, update)

        self.cleanup_current_state(context.user_data)
        context.user_data['rsi_selection_type'] = rsi_type
        context.user_data['intermediate_rsi_selection'] = {
            "enter": strategy_config.long_buy_rsi_enter if rsi_type == "long" else strategy_config.short_sell_rsi_enter,
            "dca": strategy_config.long_buy_additional_enter if rsi_type == "long" else strategy_config.short_sell_additional_enter,
            "exit": strategy_config.long_buy_rsi_exit if rsi_type == "long" else strategy_config.short_sell_rsi_exit
        }
        context.user_data['intermediate_rsi_config'] = copy.deepcopy(user_strategy.strategy_config)

        is_short = context.user_data['rsi_selection_type'] == 'short'
        old_config = strategy_config.dump(risks=False, long_rsi=not is_short, short_rsi=is_short, pos_size=False)

        text = (f"{current_strategy_name}\n"
                f"{'🍎 *Short RSI*' if is_short else '🍏 *Long RSI*'} {'settings ⚙️'}\n" +
                f"{old_config.splitlines()[1]}\n")

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📍 Entry", callback_data="setup_rsi_enter"),
             InlineKeyboardButton("🔄 DCA", callback_data="setup_rsi_dca"),
             InlineKeyboardButton("🏁 Exit", callback_data="setup_rsi_exit")],
            [InlineKeyboardButton('↩️ Back', callback_data="setup_rsi_discard"),
             InlineKeyboardButton('💾 Save', callback_data="setup_rsi_save")]
        ])

        status_message = await message.reply_text(f"{text}", parse_mode="Markdown",
                                                  reply_markup=reply_markup)
        context.user_data['last_rsi_status_message'] = status_message.message_id

    @safe_handler
    async def rsi_start_edit(self, update, context):
        query = update.callback_query

        message_text = query.message.text
        current_strategy, current_strategy_name = self.determine_current_strategy(message_text, context.user_data)

        await query.answer()
        selection_step = query.data.replace("setup_rsi_", "")
        context.user_data['rsi_selection_step'] = selection_step

        discard_markup = InlineKeyboardMarkup([[InlineKeyboardButton('↩️ Back', callback_data="setup_rsi_discard")]])
        context.user_data['active_rsi_selection'] = True
        context.user_data['active_rsi_selection_strategy'] = current_strategy
        context.user_data['active_rsi_selection_strategy_name'] = current_strategy_name

        if selection_step == "enter":
            text = (f'{current_strategy_name}\n\n'
                    '📍 Select *entry* RSI\n'
                    f'_Type new value_ 👇')
        elif selection_step == "dca":
            text = (f'{current_strategy_name}\n\n'
                    '🔄 Select *DCA* RSI\n'
                    f'_Type new value_ 👇')
        elif selection_step == "exit":
            text = (f'{current_strategy_name}\n\n'
                    '🏁 Select *exit* RSI\n'
                    f'_Type new value_ 👇\n')
        elif selection_step == "save":
            await self.rsi_setup_save_changes(update, context, current_strategy, current_strategy_name)
            return
        else:  # discard
            await self.discard_message(update, context)
            self.cleanup_current_state(context.user_data)
            return

        await self.delete_last_rsi_selection_message(context, update)
        message = await query.message.reply_text(f"{text}", parse_mode="Markdown",
                                        reply_markup=discard_markup)
        context.user_data['selection_message_id'] = message.message_id

    @safe_handler
    async def delete_last_rsi_selection_message(self, context, update):
        if 'selection_message_id' in context.user_data:
            await context.bot.delete_message(chat_id=update.effective_chat.id,
                                             message_id=context.user_data['selection_message_id'])

    @safe_handler
    async def rsi_setup_enter_number(self, update, context, current_strategy, current_strategy_name):
        user_id = update.effective_user.id

        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)
        strategy_config = user_strategy.strategy_config

        current_selection_step = context.user_data['rsi_selection_step'] if 'rsi_selection_step' in context.user_data else None

        user_text = update.message.text
        if not user_text.isdigit() or not (1 <= int(user_text) <= 99):
            discard_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton('↩️ Back', callback_data="discard_message")]])
            text = "❌ Please enter a valid number in range 1-99"
            await update.message.reply_text(f"{text}", parse_mode="Markdown",
                                            reply_markup=discard_markup)
            return

        context.user_data['intermediate_rsi_selection'][current_selection_step] = int(user_text)
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id,
                                       message_id=context.user_data['selection_message_id'])
            await update.message.delete()
            self.cleanup_current_state(context.user_data, full=False)
        except Exception as e:
            log_error(f"Error during rsi message delete: {e}\n"
                      f"{traceback.format_exc()}")

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📍 Entry", callback_data="setup_rsi_enter"),
             InlineKeyboardButton("🔄 DCA", callback_data="setup_rsi_dca"),
             InlineKeyboardButton("🏁 Exit", callback_data="setup_rsi_exit")],
            [InlineKeyboardButton('↩️ Back', callback_data="setup_rsi_discard"),
             InlineKeyboardButton('💾 Save', callback_data="setup_rsi_save")]
        ])

        is_short = context.user_data['rsi_selection_type'] == 'short'
        current_config = context.user_data['intermediate_rsi_config']
        old_config = strategy_config.dump(risks=False, long_rsi=not is_short, short_rsi=is_short, pos_size=False)

        intermediate_rsi = context.user_data['intermediate_rsi_selection']
        if is_short:
            current_config.setup_short_position(intermediate_rsi['enter'], intermediate_rsi['dca'], intermediate_rsi['exit'])
        else:
            current_config.setup_long_position(intermediate_rsi['enter'], intermediate_rsi['dca'], intermediate_rsi['exit'])

        new_config = current_config.dump(risks=False, long_rsi=not is_short, short_rsi=is_short, pos_size=False)
        is_changed = new_config.splitlines()[1] != old_config.splitlines()[1]
        text = (f"{current_strategy_name}\n\n"
                f"{'🍎 *Short RSI*' if is_short else '🍏 *Long RSI*'} {'settings ⚙️'}\n" +
                (f"_Was:_\n" if is_changed else '') +
                f"{old_config.splitlines()[1]}\n" +
                (f"*New:*\n"
                f"{new_config.splitlines()[1]}\n" if is_changed else ''))

        await self.remove_last_rsi_status_message(context, update)
        message = update.message
        status_message = await message.reply_text(f"{text}", parse_mode="Markdown",
                                 reply_markup=reply_markup)

        context.user_data['last_rsi_status_message'] = status_message.message_id

    async def rsi_setup_save_changes(self, update, context, current_strategy, current_strategy_name):
        user_id = update.effective_user.id
        user_strategy = self.user_manager.get(user_id).strategies.get_strategy(current_strategy)

        strategy_config = user_strategy.strategy_config

        discard_markup = InlineKeyboardMarkup([[InlineKeyboardButton('↩️ Back', callback_data="setup_rsi_discard")]])
        intermediate_rsi = context.user_data['intermediate_rsi_selection']

        reply_markup = discard_markup

        await self.remove_last_rsi_status_message(context, update)

        is_short = context.user_data['rsi_selection_type'] == 'short'
        old_config = strategy_config.dump(risks=False, long_rsi=not is_short, short_rsi=is_short, pos_size=False)

        if is_short:
            strategy_config.setup_short_position(intermediate_rsi['enter'], intermediate_rsi['dca'],
                                                intermediate_rsi['exit'])
        else:
            strategy_config.setup_long_position(intermediate_rsi['enter'], intermediate_rsi['dca'],
                                               intermediate_rsi['exit'])

        strategy_config.store(current_strategy)

        new_config = strategy_config.dump(risks=False, long_rsi=not is_short, short_rsi=is_short, pos_size=False)
        is_changed = new_config.splitlines()[1] != old_config.splitlines()[1]
        text = (f"{current_strategy_name}\n"
                f"{'🍎 *Short RSI*' if is_short else '🍏 *Long RSI*'} settings saved 💾\n\n" +
                (f"_Was:_\n" if is_changed else '') +
                f"{old_config.splitlines()[1]}\n" +
                (f"*New:*\n"
                 f"{new_config.splitlines()[1]}\n" if is_changed else ''))

        message = update.callback_query.message
        status_message = await message.reply_text(f"{text}", parse_mode="Markdown",
                                                  reply_markup=reply_markup)
        context.user_data['last_rsi_status_message'] = status_message.message_id
        self.cleanup_current_state(context.user_data)

    @safe_handler
    async def remove_last_rsi_status_message(self, context, update):
        if 'last_rsi_status_message' in context.user_data:
            await context.bot.delete_message(chat_id=update.effective_chat.id,
                                             message_id=context.user_data['last_rsi_status_message'])

    @safe_handler
    async def overview(self, update, context):
        await self.handle_market_overview_toggle(update, context)



bot_handler = None

def run_bot_server(user_manager):
    """
    Function to initialize the bot and run it asynchronously.
    """
    # Initialize the bot handler

    # Create the bot application
    application = Application.builder().token(LogConfig.TELEGRAM_TOKEN).build()
    global bot_handler
    bot_handler = BotHandler(user_manager, application)

    # Add command handlers
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(CommandHandler("help", bot_handler.start))
    application.add_handler(MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=bot_handler.handle_user_response))

    application.add_handler(CallbackQueryHandler(bot_handler.overview, pattern="toggle"))
    application.add_handler(CallbackQueryHandler(bot_handler.overview, pattern="more"))
    application.add_handler(CallbackQueryHandler(bot_handler.overview, pattern="display"))
    application.add_handler(CallbackQueryHandler(bot_handler.strategy_settings_risk_management, pattern="strategy_settings_risk_management"))
    application.add_handler(CallbackQueryHandler(bot_handler.strategy_settings_size, pattern="strategy_settings_position_"))
    application.add_handler(CallbackQueryHandler(bot_handler.strategy_settings, pattern="current_strategy_settings_refresh"))

    application.add_handler(CallbackQueryHandler(bot_handler.setup_strategy_settings, pattern="setup_strategy_settings_"))
    application.add_handler(CallbackQueryHandler(bot_handler.rsi_start_edit, pattern="setup_rsi_"))
    application.add_handler(CallbackQueryHandler(bot_handler.discard_message, pattern="discard_message"))

    application.add_handler(CallbackQueryHandler(bot_handler.strategies, pattern="strategies_menu"))
    application.add_handler(CallbackQueryHandler(bot_handler.show_strategy_menu, pattern="strategy_menu"))

    application.add_handler(CallbackQueryHandler(bot_handler.dump_position_history, pattern="history"))

    set_bot_commands_sync()

    # loop.close()
    application.run_polling()

