def calculate_intersection_price(ema7, ema50, period7=7, period50=50):
    """
    Находит цену пересечения EMA(7) и EMA(50) аналитически.

    :param ema7: Текущее значение EMA(7).
    :param ema50: Текущее значение EMA(50).
    :param period7: Период EMA(7) (по умолчанию 7).
    :param period50: Период EMA(50) (по умолчанию 50).
    :return: Цена пересечения.
    """
    # Коэффициенты сглаживания для EMA
    alpha7 = 2 / (period7 + 1)
    alpha50 = 2 / (period50 + 1)

    # Решаем уравнение для цены пересечения
    intersection_price = (alpha7 * ema7 - alpha50 * ema50) / (alpha7 - alpha50)
    return intersection_price

# Пример использования
ema7 = 72318  # Текущее значение EMA(7)
ema50 = 71803 # Текущее значение EMA(50)

intersection_price = calculate_intersection_price(ema7, ema50)
print("Цена пересечения EMA(7) и EMA(50):", intersection_price)
