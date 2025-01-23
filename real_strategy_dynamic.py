import datetime
import threading
import time
import traceback

import market_overview
from config import RealTimeConfig
from fake_server import run_web_server
from historical_data_loader import HistoricalDataLoader
from logger_output import log_error
from state import UserManager
from tg_input import run_bot_server
from trade_logic import trade_logic

threading.Thread(target=run_web_server, daemon=True).start()

user_manager = UserManager()
history_data_loader = HistoricalDataLoader()

def main_loop():
    while True:
        try:
            def is_first_minute():
                current_minute = datetime.datetime.now().minute
                return current_minute == 1

            if RealTimeConfig.first_minute_check and not is_first_minute():
                time.sleep(60)
                continue

            update = history_data_loader.get_update()
            if update:
                row, previous_row, timestamp = update
                try:
                    market_overview.overview_printer.append_market_overview(row, previous_row)
                except Exception as e:
                    log_error(f"Failed to append market overview! {e}\n"
                              f"{traceback.format_exc()}")
                latest_price = row['close']

                for user_data in list(user_manager.users.values()):
                    for strategy in user_data.strategies.strategies.values():
                        trade_logic(row, strategy=strategy, timestamp=timestamp, latest_price=latest_price, user=user_data)

            if not RealTimeConfig.first_minute_check:
                time.sleep(60)

        except Exception as e:
            log_error(f"Error occurred: {e}\n"
                f"{traceback.format_exc()}")
            time.sleep(300)  # Ожидание перед повторной попыткой


threading.Thread(target=main_loop, daemon=True).start()
try:
    run_bot_server(user_manager)
except Exception as e:
    log_error(f"Running bot failed! {e}\n"
              f"{traceback.format_exc()}")
