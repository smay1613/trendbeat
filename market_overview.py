import datetime
from collections import deque

import pytz

from config import BacktestConfig
from formatting import format_price
from indicators import get_btc_dominance, get_fear_and_greed_index
from chart import fetch_chart
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

def characterize_adx(adx_value):
    if adx_value < 15:
        return "No Trend"
    elif 15 <= adx_value < 25:
        return "Noticeable"
    elif 25 <= adx_value < 40:
        return "Strong"
    elif 40 <= adx_value < 60:
        return "Very Strong"
    else:
        return "Overheated"

# def get_price(symbol):
#     Получение текущей рыночной цены
    # ticker = client.futures_symbol_ticker(symbol=symbol)
    # return float(ticker['price'])


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
    # trend_icon = "📈" if change > 0 else "📉"
    trend_icon = '↑' if change >= 0 else '↓'
    return f"_({change:+.1f}%)_ {trend_icon}"

def format_value_change(current_value, previous_value, format_as_price=False, print_previous_value=False):
    change = round(current_value - previous_value, 1)

    # trend_icon = "📈" if change > 0 else "📉" if change < 0 else "➖"
    trend_icon = '↑' if change >= 0 else '↓'
    if format_as_price:
        change = f'{format_price(change, diff=True)}'
    else:
        def format_number(value):
            return f"{value:+.1f}".rstrip('0').rstrip('.')

        change = f'{format_number(change)}'
    if print_previous_value:
        prev_value = f'`{f"{previous_value }" if not format_as_price else (format_price(previous_value) + " ")}`'
    else:
        prev_value = ''
    return f"{prev_value}_{change}_ {trend_icon}"

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

def format_ema(formatted_data, previous_formatted_data):
    # TODO: BROKEN EMAS

    current_price = formatted_data['close']

    def broken_icon(ema_type):
        previous_price = previous_formatted_data['close']
        was_lower = previous_price < previous_formatted_data[ema_type]
        was_bigger = previous_price > previous_formatted_data[ema_type]

        is_broken = (was_lower and current_price > formatted_data[ema_type]) \
                    or (was_bigger and current_price < formatted_data[ema_type])
        # current price was lower than ema, now bigger than ema
        # or current price was biger than ema, now less than ema
        return ' 💥' if is_broken else ''

    emas = [('EMA  7 _(Active)_', formatted_data['EMA_7'], '🔺' if formatted_data['EMA_7'] > previous_formatted_data['EMA_7'] else '🔻', broken_icon('EMA_7')),
            ('EMA 25 _(Short)_', formatted_data['EMA_25'], '🔺' if formatted_data['EMA_25'] > previous_formatted_data['EMA_25'] else '🔻', broken_icon('EMA_25')),
            ('EMA 50 _(Base)_', formatted_data['EMA_99'], '🔺' if formatted_data['EMA_99'] > previous_formatted_data['EMA_99'] else '🔻', broken_icon('EMA_99'))]
    sorted_emas = sorted(emas, key=lambda x: int(x[1]), reverse=True)

    def pin(upper_band, lower_band):
        # Определение ближайшей границы
        upper_diff = abs(current_price - upper_band)
        lower_diff = abs(current_price - lower_band)

        if upper_diff < lower_diff:
            return f"📍 Price:                   `{format_price(current_price)}` ↑"
        else:
            return f"📍 Price:                   `{format_price(current_price)}` ↓"

    # Проверка текущей цены относительно верхней и нижней границы
    # upper_broken = current_price >= previous_formatted_data['BB_UPPER']
    # lower_broken = current_price <= previous_formatted_data['BB_LOWER']
    upper_band = sorted_emas[0][1]
    middle_band = sorted_emas[1][1]
    lower_band = sorted_emas[2][1]

    graph = ""

    # Формирование строки
    if current_price > middle_band:  # Цена выше средней линии
        if current_price > upper_band:
            graph += f"{pin(current_price, upper_band)}\n"
            for sorted_ema in sorted_emas:
                graph += f'{sorted_ema[2]} {sorted_ema[0]}:   `{format_price(sorted_ema[1])}` {sorted_ema[3]}\n'
        else:
            for sorted_ema in [sorted_emas[0]]:
                graph += f'{sorted_ema[2]} {sorted_ema[0]}:   `{format_price(sorted_ema[1])}` {sorted_ema[3]}\n'
            graph += f"{pin(upper_band, middle_band)}\n"
            for sorted_ema in sorted_emas[1:]:
                graph += f'{sorted_ema[2]} {sorted_ema[0]}:   `{format_price(sorted_ema[1])}` {sorted_ema[3]}\n'
    else:  # Цена ниже средней линии
        if current_price < lower_band:
            for sorted_ema in sorted_emas:
                graph += f'{sorted_ema[2]} {sorted_ema[0]}:   `{format_price(sorted_ema[1])}` {sorted_ema[3]}\n'
            graph += f"{pin(lower_band, current_price)}\n"
        else:
            for sorted_ema in sorted_emas[:2]:
                graph += f'{sorted_ema[2]} {sorted_ema[0]}:   `{format_price(sorted_ema[1])}` {sorted_ema[3]}\n'
            graph += f"{pin(upper_band, middle_band)}\n"
            for sorted_ema in [sorted_emas[2]]:
                graph += f'{sorted_ema[2]} {sorted_ema[0]}:   `{format_price(sorted_ema[1])}` {sorted_ema[3]}\n'

    return graph

def btc_dominance_level_description(current_dominance):
    """
    Функция для текстового описания уровня BTC Dominance на основе текущего значения.

    :param current_dominance: Текущее значение BTC Dominance (в процентах).
    :return: Строка с текстовым описанием текущего уровня BTC Dominance.
    """
    if current_dominance >= 70:
        return f"_high_ | 🟢"
    elif 60 <= current_dominance < 70:
        return f"_moderate_ | 🟡"
    elif 50 <= current_dominance < 60:
        return f"_neutral_ | 🟠"
    elif 40 <= current_dominance < 50:
        return f"_low_ | 🔴"
    else:
        return f"_very low_ | 🔴"

def get_trading_session():
    # Задаем временные зоны для каждой сессии
    timezone_utc = pytz.timezone('UTC')

    # Время начала и окончания торговых сессий в UTC
    sessions = {
        'american': {'start': 14, 'end': 22},  # с 14:00 до 22:00 UTC
        'european': {'start': 7, 'end': 15},   # с 7:00 до 15:00 UTC
        'asian': {'start': 0, 'end': 8},       # с 0:00 до 8:00 UTC
    }

    # Получаем текущее время по UTC
    now_utc = datetime.datetime.now(timezone_utc)

    # Определяем сессию
    if sessions['american']['start'] <= now_utc.hour < sessions['american']['end']:
        return 'American'
    elif sessions['european']['start'] <= now_utc.hour < sessions['european']['end']:
        return 'European'
    elif sessions['asian']['start'] <= now_utc.hour < sessions['asian']['end']:
        return 'Asian'
    else:
        return 'Outside Trading Hours'

class OverviewPrinter:
    def __init__(self):
        self.max_overviews = 48
        self.last_market_overviews = deque(maxlen=self.max_overviews)

    def append_market_overview(self, row, previous_row):
        trend, trend_type = determine_trend(row)
        formatted_data = {key: value for key, value in list(row.to_dict().items())}
        previous_formatted_data = {key: value for key, value in list(previous_row.to_dict().items())}

        dominance_now, dominance_yesterday = get_btc_dominance()
        # trend_icon_separator = '🔺' if trend == 'LONG' else '🔻'
        fear_and_greed_value, fear_and_greed_text, fear_and_greed_value_yesterday, fear_and_greed_text_yesterday = get_fear_and_greed_index()

        separator = '▫️'
        # section_separator = "---\n"

        overview = {}

        overview['Session'] = get_trading_session()
        overview['Timestamp'] = datetime.datetime.utcnow().strftime("%d.%m %H:%M")

        overview['Price'] = (
            f"\n💰 *Price*\n"
            f"{separator} Now:   `{format_price(formatted_data['close'])}` | "
            f"{format_value_change(float(formatted_data['close']), float(previous_formatted_data['close']), format_as_price=True)}\n"
            f"{separator} Range:  `{format_price(formatted_data['low'])} - {format_price(formatted_data['high'])}`\n"
        )

        overview['Volume'] = (
            f"\n📊 *Volume*\n"
            f"{separator} `{formatted_data['volume']:.0f}` | {format_value_change(int(float(formatted_data['volume'])), int(float(previous_formatted_data['volume'])), print_previous_value=False)} | "
            f"_avg:_ `{formatted_data['Average_Volume']:.0f}` | {decision_icon(formatted_data['volume'] > formatted_data['Average_Volume'])}\n"
        )

        overview['RSI'] = (
            f"\n{rsi_condition_icon(formatted_data['RSI_6'])} *RSI* (_6{BacktestConfig.interval_period}_)\n"
            f"{separator} `{formatted_data['RSI_6']:.1f}` | {format_value_change(round(float(formatted_data['RSI_6']), 1), round(float(previous_formatted_data['RSI_6']), 1))} | "
            f"_{rsi_conditions(formatted_data['RSI_6'])}_ | {decision_icon(rsi_conditions(formatted_data['RSI_6']) == 'neutral')}\n"
        )

        overview['Trend'] = (
            f"\n📌 *Market Trend*\n"
            f"{separator} Direction: `{trend.capitalize()}` | `{trend_type.capitalize()}` | {trend_icon(trend, trend_type)}\n"
            f"{separator} Strength (ADX): `{formatted_data['ADX']:.0f}` | _{characterize_adx(formatted_data['ADX'])}_ | {decision_icon(formatted_data['ADX'] > 15)}\n"
        )

        overview['EMA'] = (
            f"\n📊 *EMA Indicators* \n"
            + format_ema(formatted_data, previous_formatted_data)
        )

        overview['Bollinger'] = (
            f"\n📏 *Bollinger Bands*\n"
            + format_bands(formatted_data, previous_formatted_data)
        )

        overview['Support'] = (
            f"\n📉 *Support Levels*\n"
            f"🔹 Immediate (_7{BacktestConfig.interval_period}_):     `{format_price(formatted_data['Support_7'])}` {support_check_message(formatted_data, previous_formatted_data, 'Support_7')}\n"
            f"🔹 Short term (_25{BacktestConfig.interval_period}_):   `{format_price(formatted_data['Support_25'])}` {support_check_message(formatted_data, previous_formatted_data, 'Support_25')}\n"
            f"🔹 Mid term (_50{BacktestConfig.interval_period}_):     `{format_price(formatted_data['Support_50'])}` {support_check_message(formatted_data, previous_formatted_data, 'Support_50')}\n"
            f"🔹 Long term (_99{BacktestConfig.interval_period}_):    `{format_price(formatted_data['Support_99'])}` {support_check_message(formatted_data, previous_formatted_data, 'Support_99')}\n"
        )

        overview['Resistance'] = (
            f"\n📈 *Resistance Levels*\n"
            f"🔸 Immediate (_7{BacktestConfig.interval_period}_):     `{format_price(formatted_data['Resistance_7'])}` {resistance_check_message(formatted_data, previous_formatted_data, 'Resistance_7')}\n"
            f"🔸 Short term (_25{BacktestConfig.interval_period}_):   `{format_price(formatted_data['Resistance_25'])}` {resistance_check_message(formatted_data, previous_formatted_data, 'Resistance_25')}\n"
            f"🔸 Mid term (_50{BacktestConfig.interval_period}_):     `{format_price(formatted_data['Resistance_50'])}` {resistance_check_message(formatted_data, previous_formatted_data, 'Resistance_50')}\n"
            f"🔸 Long term (_99{BacktestConfig.interval_period}_):    `{format_price(formatted_data['Resistance_99'])}` {resistance_check_message(formatted_data, previous_formatted_data, 'Resistance_99')}\n"
        )

        overview['Dominance'] = (
            "\n⚖️ *BTC Dominance*\n"
            f"{separator} `{dominance_now:.1f}%` | {format_btc_dominance(dominance_now, dominance_yesterday)} | {btc_dominance_level_description(dominance_now)}\n"
        )

        overview['FearAndGreed'] = (
            f"\n{fear_and_greed_icon(fear_and_greed_value)} *Fear & Greed*\n"
            f"{separator} `{fear_and_greed_value}` | {format_value_change(fear_and_greed_value, fear_and_greed_value_yesterday)} | _{fear_and_greed_text.lower()}_ | {fear_and_greed_status_icon(fear_and_greed_value)}\n"
        )

        overview['ChartURL'] = fetch_chart()

        self.last_market_overviews.append(overview)

        return overview

    def get_last(self, settings=None, display_settings=None, index=-1):
        return self.overview_to_text(self.last_market_overviews[index] if len(self.last_market_overviews) else None, settings, display_settings)

    def overview_to_text(self, overview, settings=None, display_settings=None):
        if not overview:
            return "💤 Overview is not collected yet"
        all_enabled = not display_settings
        price_enabled = not settings or settings['price']
        trend_enabled = not settings or settings['trend']
        support_resistance_enabled = not settings or settings['support_resistance']
        sentiment_enabled = not settings or settings['sentiment']

        has_price_section = all_enabled or display_settings['price'] or display_settings['volume'] or display_settings['rsi']
        has_trend_section = all_enabled or display_settings['trend'] or display_settings['ema'] or display_settings['bands']
        has_key_levels_section = all_enabled or display_settings['support'] or display_settings['resistance']
        has_sentiment_section = all_enabled or display_settings['dominance'] or display_settings['sentiment']

        section_separator = "──────────\n"
        chart_link = f"[Market Overview]({overview['ChartURL']})" if overview['ChartURL'] else "*Market Overview*"
        msg = (
            f"🌎 *{BacktestConfig.symbol}* {chart_link} | {BacktestConfig.interval} {('| _' + overview['Session'] + '_')}\n"
            f"🕓 {overview['Timestamp']}\n"
            f"{section_separator}" +
            (
                (
                    (overview['Price'] if all_enabled or display_settings['price'] else '') +
                    (overview['Volume'] if all_enabled or display_settings['volume'] else '') +
                    (overview['RSI'] if all_enabled or display_settings['rsi'] else '') +
                 f"{section_separator if has_price_section else ''}"
                ) if price_enabled else ''
             ) +
            (
                (
                    (overview['Trend'] if all_enabled or display_settings['trend'] else '') +
                    (overview['EMA'] if all_enabled or display_settings['ema'] else '') +
                    (overview['Bollinger'] if all_enabled or display_settings['bands'] else '') +
                    f"{section_separator if has_trend_section else ''}"
                ) if trend_enabled else ''
            ) +
            (
                (
                    (overview['Support'] if all_enabled or display_settings['support'] else '') +
                    (overview['Resistance'] if all_enabled or display_settings['resistance'] else '') +
                    f"{section_separator if has_key_levels_section else ''}"
                ) if support_resistance_enabled else ''
            ) +
            (
                (
                    (overview['Dominance'] if all_enabled or display_settings['dominance'] else '') +
                    (overview['FearAndGreed'] if all_enabled or display_settings['sentiment'] else '') +
                    f"{section_separator if has_sentiment_section else ''}"
                ) if sentiment_enabled else ''
            )
        )

        return msg
overview_printer = OverviewPrinter()
