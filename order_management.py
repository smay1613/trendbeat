from binance.client import Client

from config import BacktestConfig, StrategyConfig, ConnectionsConfig
from logger_output import log
from state import PositionState

client = Client(ConnectionsConfig.TESTNET_API_KEY, ConnectionsConfig.TESTNET_API_SECRET, testnet=ConnectionsConfig.testnet_orders)

def get_price(symbol):
    # Получение текущей рыночной цены
    ticker = client.futures_symbol_ticker(symbol=symbol)
    return float(ticker['price'])


def open_position(position_side, position_state):
    if not BacktestConfig.send_orders:
        return
    # Получаем текущую цену актива
    price = get_price(BacktestConfig.symbol)

    # Рассчитываем количество актива с учетом кредитного плеча
    quantity = (StrategyConfig.position_size * BacktestConfig.LEVERAGE) / price
    quantity = round(quantity, 3)  # Округляем до нужного количества знаков после запятой
    position_state.position_qty = quantity

    # Открываем рыночный ордер на покупку (лонг)
    try:
        order = client.futures_create_order(
            symbol=BacktestConfig.symbol,
            positionSide=position_side,
            side='BUY' if position_side == 'LONG' else 'SELL',
            type='LIMIT',
            quantity=quantity,
            price=price,
            timeinforce='GTC'
        )
        log(f"Position opened: {order}")

        return order
    except Exception as e:
        log(f"Error during position open: {e}")

    return None


def close_position(position_side, position_state):
    if not BacktestConfig.send_orders:
        return
    # Получаем текущую цену актива
    price = get_price(BacktestConfig.symbol)

    try:
        # Закрываем позицию (обратный ордер к открытому)
        order = client.futures_create_order(
            symbol=BacktestConfig.symbol,
            positionSide=position_side,
            side='SELL' if position_side == 'LONG' else 'BUY',  # Для закрытия шорта используйте 'BUY'
            type='LIMIT',
            quantity=position_state.position_qty,
            price=price,
            timeinforce='GTC'
        )
        log(f"Position closed: {order}")
        return order
    except Exception as e:
        log(f"Error during position close: {e}")
        # try again?

    return None