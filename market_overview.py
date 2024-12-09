from config import StrategyConfig, BacktestConfig
from indicators import get_btc_dominance, get_fear_and_greed_index
from logger_output import log
from trade_logic import determine_trend


def rsi_conditions(rsi):
    if rsi > 82:
        return "strong overbuy"
    elif rsi > 68:
        return "overbuy"
    elif rsi < 35:
        return "oversell"
    elif rsi < 27:
        return "strong oversell"

    return "neutral"


def rsi_condition_icon(rsi):
    condition = rsi_conditions(rsi)
    return "🔴" if "oversell" in condition else \
        "🟡" if "overbuy" in condition else \
            '🟢'


def decision_icon(is_good):
    return '✅' if is_good else '⚠️'


def trend_icon(trend, type):
    return "🔼" if trend == "LONG" and type == "WEAK" else "⏫" if trend == "LONG" else \
        "🔽" if type == "WEAK" else "⏬"

def fear_and_greed_status_icon(greed_value):
    if 0 <= greed_value <= 24:
        return "🟥"  # Extreme Fear
    elif 25 <= greed_value <= 49:
        return "🟧"  # Fear
    elif greed_value == 50:
        return "🟨"  # Neutral
    elif 51 <= greed_value <= 74:
        return "🟩"  # Greed
    elif 75 <= greed_value <= 100:
        return "🟩"  # Extreme Greed
    else:
        return "❓"

def fear_and_greed_icon(greed_value):
    if 0 <= greed_value <= 24:
        return "😱"  # Extreme Fear
    elif 25 <= greed_value <= 49:
        return "😟"  # Fear
    elif greed_value == 50:
        return "😐"  # Neutral
    elif 51 <= greed_value <= 74:
        return "😎"  # Greed
    elif 75 <= greed_value <= 100:
        return "🤑"  # Extreme Greed
    else:
        return "❓"

def get_price(symbol):
    # Получение текущей рыночной цены
    ticker = client.futures_symbol_ticker(symbol=symbol)
    return float(ticker['price'])


def format_price(price, diff=False):
    return f'{int(price):,}$' if not diff else f'{"+" if price >= 0 else ""}{int(price):,}$'

def support_check_message(formatted_data, previous_formatted_data, support_level):
    if formatted_data[support_level] >= previous_formatted_data[support_level]:
        return ''
    return f' ⚠️\n💥 `{format_price(previous_formatted_data[support_level])}` 📉'

def resistance_check_message(formatted_data, previous_formatted_data, resist_level):
    if formatted_data[resist_level] <= previous_formatted_data[resist_level]:
        return ''
    return f' ⚠️\n💥 `{format_price(previous_formatted_data[resist_level])}` 📈'

def format_btc_dominance(current_dominance, previous_dominance):
    change = current_dominance - previous_dominance
    trend_icon = "📈" if change > 0 else "📉"
    return f"`{previous_dominance}%` _({change:+.1f}%)_ {trend_icon}"

def format_value_change(current_value, previous_value, format_as_price=False):
    change = round(current_value - previous_value, 1)

    trend_icon = "📈" if change > 0 else "📉" if change < 0 else "➖"
    if format_as_price:
        change = f'({format_price(change, diff=True)})'
    else:
        def format_number(value):
            return f"{value:+.1f}".rstrip('0').rstrip('.')

        change = f'({format_number(change)})'

    return f"`{previous_value if not format_as_price else format_price(previous_value)}` _{change}_ {trend_icon}"

def format_bands(formatted_data, previous_formatted_data):
    def broken_icon(is_broken):
        return ' 💥' if is_broken else ''

    current_price = formatted_data['close']

    def pin(upper_band, lower_band, middle_band):
        # Определение ближайшей границы
        upper_diff = abs(current_price - upper_band)
        lower_diff = abs(current_price - lower_band)
        middle_diff = abs(current_price - middle_band)

        if current_price < middle_band:
            if middle_diff < lower_diff:
                return f"📍 Price: `{format_price(current_price)}` ↑"
            else:
                return f"📍 Price: `{format_price(current_price)}` ↓"
        else:
            if upper_diff < middle_diff:
                return f"📍 Price: `{format_price(current_price)}` ↑"
            else:
                return f"📍 Price: `{format_price(current_price)}` ↓"

    # Проверка текущей цены относительно верхней и нижней границы
    upper_broken = current_price >= previous_formatted_data['BB_UPPER']
    lower_broken = current_price <= previous_formatted_data['BB_LOWER']

    # Формирование строки
    if current_price > formatted_data['BB_MIDDLE']:  # Цена выше средней линии
        return (
            f"🔺 Up:    `{format_price(formatted_data['BB_UPPER'])}`{broken_icon(upper_broken)}\n"
            f"{pin(formatted_data['BB_UPPER'], formatted_data['BB_MIDDLE'], formatted_data['BB_MIDDLE'])}\n"
            f"🔴 Mid:   `{format_price(formatted_data['BB_MIDDLE'])}`\n"
            f"🔻 Low:   `{format_price(formatted_data['BB_LOWER'])}`\n"
        )
    else:  # Цена ниже средней линии
        return (
            f"🔺 Up:   `{format_price(formatted_data['BB_UPPER'])}`\n"
            f"🔴 Mid:  `{format_price(formatted_data['BB_MIDDLE'])}`\n"
            f"{pin(formatted_data['BB_MIDDLE'], formatted_data['BB_LOWER'], formatted_data['BB_MIDDLE'])}\n"
            f"🔻 Low:  `{format_price(formatted_data['BB_LOWER'])}`{broken_icon(lower_broken)}\n"
        )


def btc_dominance_level_description(current_dominance):
    """
    Функция для текстового описания уровня BTC Dominance на основе текущего значения.

    :param current_dominance: Текущее значение BTC Dominance (в процентах).
    :return: Строка с текстовым описанием текущего уровня BTC Dominance.
    """
    if current_dominance >= 70:
        return f"_(high)_ 🟢"
    elif 60 <= current_dominance < 70:
        return f"_(moderate)_ 🟡"
    elif 50 <= current_dominance < 60:
        return f"_(neutral)_ 🟠"
    elif 40 <= current_dominance < 50:
        return f"_(low)_ 🔴"
    else:
        return f"_(very low)_ 🔴"


def log_market_overview(row, previous_row):
    trend, trend_type = determine_trend(row)
    formatted_data = {key: value for key, value in list(row.to_dict().items())}
    previous_formatted_data = {key: value for key, value in list(previous_row.to_dict().items())}

    dominance_now, dominance_yesterday = get_btc_dominance()
    trend_icon_separator = '🔺' if trend == 'LONG' else '🔻'
    fear_and_greed_value, fear_and_greed_text, fear_and_greed_value_yesterday, fear_and_greed_text_yesterday = get_fear_and_greed_index()

    separator = '▫️'
    section_separator = "---\n"

    return (
        f"*{BacktestConfig.symbol} Market Overview*\n"
        f"\n📌 *Market Trend*\n"
        f"{separator} Direction: `{trend}` | `{trend_type}` {trend_icon(trend, trend_type)}\n"
        f"{separator} Strength (ADX): `{formatted_data['ADX']:.0f}` (_min_ `{StrategyConfig.min_adx}`) {decision_icon(formatted_data['ADX'] > StrategyConfig.min_adx)}\n"
        f"{section_separator}"
        "\n⚖️ *BTC Dominance*\n"
        f"{separator} Now:  `{dominance_now:.1f}%` {btc_dominance_level_description(dominance_now)}\n"
        f"{separator} Was:  {format_btc_dominance(dominance_now, dominance_yesterday)}\n"
        # f"{separator} Yesterday: {dominance_yesterday}%\n"
        f"\n{fear_and_greed_icon(fear_and_greed_value)} *Fear & Greed*\n"
        f"{separator} Now:  `{fear_and_greed_value}` _({fear_and_greed_text.lower()})_ {fear_and_greed_status_icon(fear_and_greed_value)}\n"
        f"{separator} Was:  {format_value_change(fear_and_greed_value, fear_and_greed_value_yesterday)}\n"
        # f"{separator} Yesterday: {fear_and_greed_value_yesterday} (_{fear_and_greed_text_yesterday}_)\n"
        f"{section_separator}"
        f"\n📊 *Volume*\n"
        f"{separator} Now:  `{formatted_data['volume']:.0f}` _(avg:_ `{formatted_data['Average_Volume']:.0f}`_)_ {decision_icon(formatted_data['volume'] > formatted_data['Average_Volume'])}\n"
        f"{separator} Was:  {format_value_change(int(float(formatted_data['volume'])), int(float(previous_formatted_data['volume'])))}\n"
        # f"{separator} Average:  `{formatted_data['Average_Volume']:.0f}`\n"
        f"\n{rsi_condition_icon(formatted_data['RSI_6'])} *RSI* (_6{BacktestConfig.interval_period}_)\n"
        f"{separator} Now: `{formatted_data['RSI_6']:.1f}` (_{rsi_conditions(formatted_data['RSI_6'])}_) {decision_icon(rsi_conditions(formatted_data['RSI_6']) == 'neutral')}\n"
        f"{separator} Was:  {format_value_change(round(float(formatted_data['RSI_6']), 1), round(float(previous_formatted_data['RSI_6']), 1))}\n"
        f"{section_separator}"
        f"\n💰 *Price*\n"
        f"{separator} Now:   `{format_price(formatted_data['close'])}`\n"
        f"{separator} Was:    {format_value_change(float(formatted_data['close']), float(previous_formatted_data['close']), format_as_price=True)}\n"
        f"{separator} Range:  `{format_price(formatted_data['low'])} - {format_price(formatted_data['high'])}`\n"
        f"\n📊 *EMA Indicators* \n"
        f"{trend_icon_separator} EMA 7 (_Current_):  `{format_price(formatted_data['EMA_7'])}`\n"
        f"{trend_icon_separator} EMS 25 (_Short_):   `{format_price(formatted_data['EMA_25'])}`\n"
        f"{trend_icon_separator} EMA 50 (_Mid_):      `{format_price(formatted_data['EMA_99'])}`\n"
        f"{section_separator}"
        f"\n📉 *Support Levels*\n"
        f"🔹 Immediate (_7{BacktestConfig.interval_period}_):     `{format_price(formatted_data['Support_7'])}` {support_check_message(formatted_data, previous_formatted_data, 'Support_7')}\n"
        f"🔹 Short term (_25{BacktestConfig.interval_period}_):   `{format_price(formatted_data['Support_25'])}` {support_check_message(formatted_data, previous_formatted_data, 'Support_25')}\n"
        f"🔹 Mid term (_50{BacktestConfig.interval_period}_):     `{format_price(formatted_data['Support_50'])}` {support_check_message(formatted_data, previous_formatted_data, 'Support_50')}\n"
        f"🔹 Long term (_99{BacktestConfig.interval_period}_):    `{format_price(formatted_data['Support_99'])}` {support_check_message(formatted_data, previous_formatted_data, 'Support_99')}\n"
        f"\n📈 *Resistance Levels*\n"
        f"🔸 Immediate (_7{BacktestConfig.interval_period}_):     `{format_price(formatted_data['Resistance_7'])}` {resistance_check_message(formatted_data, previous_formatted_data, 'Resistance_7')}\n"
        f"🔸 Short term (_25{BacktestConfig.interval_period}_):   `{format_price(formatted_data['Resistance_25'])}` {resistance_check_message(formatted_data, previous_formatted_data, 'Resistance_25')}\n"
        f"🔸 Mid term (_50{BacktestConfig.interval_period}_):     `{format_price(formatted_data['Resistance_50'])}` {resistance_check_message(formatted_data, previous_formatted_data, 'Resistance_50')}\n"
        f"🔸 Long term (_99{BacktestConfig.interval_period}_):    `{format_price(formatted_data['Resistance_99'])}` {resistance_check_message(formatted_data, previous_formatted_data, 'Resistance_99')}\n"
        f"{section_separator}"
        f"\n📊 *Bollinger Bands*\n"
        + format_bands(formatted_data, previous_formatted_data)
    )

def broadcast_market_overview(row, previous_row, users):
    market_overview_text = log_market_overview(row, previous_row)

    for user_id, user_data in users.items():
        if not user_data.user_settings.market_overview_enabled:
            continue

        log(market_overview_text, user_id)
