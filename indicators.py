import ta


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

    # Добавление уровней поддержки и сопротивления
    # TODO: tema
    # df['Support'] = df['low'].rolling(window=20).min()  # 20-периодная поддержка
    # df['Resistance'] = df['high'].rolling(window=20).max()  # 20-периодное сопротивление

    # TODO: wtf?
    df['Average_Volume'] = df['volume'].rolling(window=20).mean()

    return df
