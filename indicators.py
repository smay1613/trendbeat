import ta
import requests

def calculate_indicators(df):
    price = df['close']
    df['EMA_7'] = ta.trend.ema_indicator(price, window=7)
    df['EMA_25'] = ta.trend.ema_indicator(price, window=25)
    df['EMA_99'] = ta.trend.ema_indicator(price, window=50)
    df['RSI_6'] = ta.momentum.rsi(price, window=6)
    df['RSI_15'] = ta.momentum.rsi(price, window=15)
    # stoch = ta.momentum.stoch(df['high'], df['low'], price, window=14, smooth_window=3)
    # df['Stoch_K'] = stoch
    # df['Stoch_D'] = stoch.shift(1)

    # df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], price, window=14)
    df['ADX'] = ta.trend.adx(df['high'], df['low'], price, window=14)
    # df['MACD'] = ta.trend.macd_diff(price)
    bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)

    # Получаем верхнюю и нижнюю границы полос Боллинджера
    df['BB_UPPER'] = bb.bollinger_hband()
    df['BB_LOWER'] = bb.bollinger_lband()
    df['BB_MIDDLE'] = bb.bollinger_mavg()

    # Добавление уровней поддержки и сопротивления
    df['Support_7'] = df['low'].rolling(window=7).min()  # 20-периодная поддержка
    df['Support_25'] = df['low'].rolling(window=25).min()  # 20-периодная поддержка
    df['Support_50'] = df['low'].rolling(window=50).min()  # 20-периодная поддержка
    df['Support_99'] = df['low'].rolling(window=50).min()  # 20-периодная поддержка

    df['Resistance_7'] = df['high'].rolling(window=7).max()  # 20-периодное сопротивление
    df['Resistance_25'] = df['high'].rolling(window=25).max()  # 20-периодное сопротивление
    df['Resistance_50'] = df['high'].rolling(window=50).max()  # 20-периодное сопротивление
    df['Resistance_99'] = df['high'].rolling(window=99).max()  # 20-периодное сопротивление

    df['Average_Volume'] = df['volume'].rolling(window=50).mean()

    return df


from config import CoinmarketCapConfig

def get_btc_dominance():
    URL = 'https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest'
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': CoinmarketCapConfig.API_KEY,
    }
    response = requests.get(URL, headers=headers)
    if response.status_code == 200:
        data = response.json()
        btc_dominance = data['data']['btc_dominance']
        btc_dominance_yesterday = data['data']['btc_dominance_yesterday']
        return round(btc_dominance, 1), round(btc_dominance_yesterday, 1)
    else:
        return None


def get_fear_and_greed_index():
    URL = 'https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical'
    params = {
        'limit': 2  # Получаем только последний индекс
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': CoinmarketCapConfig.API_KEY,
    }
    response = requests.get(URL, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        latest_entry = data['data'][0]  # Последняя запись
        fear_and_greed_value = latest_entry['value']  # Значение индекса
        fear_and_greed_text = latest_entry['value_classification']  # Текстовая классификация

        yesterday_value = data['data'][1]  # Последняя запись
        fear_and_greed_value_yesterday = yesterday_value['value']  # Значение индекса
        fear_and_greed_text_yesterday = yesterday_value['value_classification']  # Текстовая классификация
        return fear_and_greed_value, fear_and_greed_text, fear_and_greed_value_yesterday, fear_and_greed_text_yesterday
    else:
        return None, None, None, None